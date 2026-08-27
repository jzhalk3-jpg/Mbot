import express from "express";
import session from "express-session";
import dotenv from "dotenv";
import multer from "multer";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

import { TelegramClient } from "telegram";
import { StringSession } from "telegram/sessions/index.js";
import { Api } from "telegram";
import { NewMessage } from "telegram/events/index.js";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

const PORT = process.env.PORT || 3000;
const API_ID = Number(process.env.API_ID);
const API_HASH = process.env.API_HASH;

if (!API_ID || !API_HASH) {
  console.error("ERROR: API_ID or API_HASH is missing in .env");
  process.exit(1);
}

const uploadsPath = path.join(__dirname, "uploads");

if (!fs.existsSync(uploadsPath)) {
  fs.mkdirSync(uploadsPath);
}

app.use(express.json({ limit: "10mb" }));

app.use(
  express.urlencoded({
    extended: true
  })
);

app.use(
  session({
    secret:
      process.env.SESSION_SECRET ||
      "telegram-web-secret-change-this",
    resave: false,
    saveUninitialized: true,
    cookie: {
      httpOnly: true,
      secure: false,
      sameSite: "lax",
      maxAge: 1000 * 60 * 60 * 24 * 30
    }
  })
);

const upload = multer({
  dest: uploadsPath,
  limits: {
    fileSize: 50 * 1024 * 1024
  }
});

const clients = new Map();

function formatError(error) {
  console.error(error);

  return (
    error?.errorMessage ||
    error?.message ||
    "حدث خطأ غير متوقع"
  );
}

function cleanPhone(phone) {
  return String(phone || "")
    .trim()
    .replace(/[^\d+]/g, "");
}

function getClient(sessionId, sessionString = "") {
  if (clients.has(sessionId)) {
    return clients.get(sessionId);
  }

  const client = new TelegramClient(
    new StringSession(sessionString),
    API_ID,
    API_HASH,
    {
      connectionRetries: 5,
      useWSS: false
    }
  );

  clients.set(sessionId, client);

  return client;
}

async function ensureClient(req) {
  const sessionString =
    req.session.telegramSession;

  if (!sessionString) {
    throw new Error("UNAUTHORIZED");
  }

  const client = getClient(
    req.sessionID,
    sessionString
  );

  if (!client.connected) {
    await client.connect();
  }

  const authorized =
    await client.checkAuthorization();

  if (!authorized) {
    throw new Error("UNAUTHORIZED");
  }

  return client;
}

function getEntityName(entity) {
  if (!entity) return "Unknown";

  if (entity.firstName || entity.lastName) {
    return `${entity.firstName || ""} ${
      entity.lastName || ""
    }`.trim();
  }

  return (
    entity.title ||
    entity.username ||
    "Telegram"
  );
}

function serializeMessage(message) {
  return {
    id: message.id,
    message: message.message || "",
    date: message.date
      ? new Date(
          message.date
        ).toISOString()
      : null,
    out: Boolean(message.out),
    senderId:
      message.senderId?.toString() || null,
    media: Boolean(message.media),
    photo:
      message.photo ? true : false,
    document:
      message.document ? true : false,
    fileName:
      message.document?.attributes
        ?.find(
          attribute =>
            attribute.className ===
            "DocumentAttributeFilename"
        )
        ?.fileName || null
  };
}

function serializeDialog(dialog) {
  const entity = dialog.entity;

  return {
    id: entity.id?.toString(),
    name: getEntityName(entity),
    username: entity.username || "",
    type: entity.className || "",
    unreadCount:
      dialog.unreadCount || 0,
    lastMessage:
      dialog.message?.message || "",
    lastMessageDate:
      dialog.message?.date
        ? new Date(
            dialog.message.date
          ).toISOString()
        : null
  };
}

/* ================================
   LOGIN
================================ */

app.post(
  "/api/auth/send-code",
  async (req, res) => {
    try {
      const phone =
        cleanPhone(req.body.phone);

      if (!phone) {
        return res.status(400).json({
          success: false,
          message:
            "أدخل رقم الهاتف"
        });
      }

      const client = getClient(
        req.sessionID
      );

      if (!client.connected) {
        await client.connect();
      }

      const result =
        await client.sendCode(
          {
            apiId: API_ID,
            apiHash: API_HASH
          },
          phone
        );

      req.session.loginPhone =
        phone;

      req.session.phoneCodeHash =
        result.phoneCodeHash;

      req.session.save(() => {});

      res.json({
        success: true,
        message:
          "تم إرسال رمز التحقق",
        viaApp:
          result.isCodeViaApp
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        message:
          formatError(error)
      });
    }
  }
);

/* ================================
   VERIFY CODE
================================ */

app.post(
  "/api/auth/verify-code",
  async (req, res) => {
    try {
      const code =
        String(
          req.body.code || ""
        ).trim();

      const phone =
        req.session.loginPhone;

      const phoneCodeHash =
        req.session.phoneCodeHash;

      if (
        !phone ||
        !phoneCodeHash
      ) {
        return res.status(400).json({
          success: false,
          message:
            "اطلب رمزًا جديدًا"
        });
      }

      if (!code) {
        return res.status(400).json({
          success: false,
          message:
            "أدخل رمز التحقق"
        });
      }

      const client =
        getClient(req.sessionID);

      const result =
        await client.invoke(
          new Api.auth.SignIn({
            phoneNumber: phone,
            phoneCodeHash,
            phoneCode: code
          })
        );

      const savedSession =
        client.session.save();

      req.session.telegramSession =
        savedSession;

      req.session.loginPhone = null;

      req.session.phoneCodeHash =
        null;

      res.json({
        success: true,
        passwordRequired: false,
        user: {
          id:
            result.user.id?.toString(),
          firstName:
            result.user.firstName || "",
          lastName:
            result.user.lastName || "",
          username:
            result.user.username || ""
        }
      });

    } catch (error) {
      const errorText =
        error?.errorMessage ||
        error?.message ||
        "";

      if (
        errorText.includes(
          "SESSION_PASSWORD_NEEDED"
        )
      ) {
        return res.status(401).json({
          success: false,
          passwordRequired: true,
          message:
            "هذا الحساب يستخدم التحقق بخطوتين"
        });
      }

      res.status(500).json({
        success: false,
        message:
          formatError(error)
      });
    }
  }
);

/* ================================
   2FA
================================ */

app.post(
  "/api/auth/verify-password",
  async (req, res) => {
    try {
      const password =
        String(
          req.body.password || ""
        );

      if (!password) {
        return res.status(400).json({
          success: false,
          message:
            "أدخل كلمة المرور"
        });
      }

      const client =
        getClient(req.sessionID);

      if (!client.connected) {
        await client.connect();
      }

      await client.signInWithPassword(
        {
          apiId: API_ID,
          apiHash: API_HASH
        },
        {
          password: async () =>
            password,

          onError: async error => {
            throw error;
          }
        }
      );

      const savedSession =
        client.session.save();

      req.session.telegramSession =
        savedSession;

      req.session.loginPhone = null;

      req.session.phoneCodeHash =
        null;

      const me =
        await client.getMe();

      res.json({
        success: true,
        user: {
          id:
            me.id?.toString(),
          firstName:
            me.firstName || "",
          lastName:
            me.lastName || "",
          username:
            me.username || ""
        }
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        message:
          formatError(error)
      });
    }
  }
);

/* ================================
   CURRENT USER
================================ */

app.get(
  "/api/me",
  async (req, res) => {
    try {
      if (
        !req.session.telegramSession
      ) {
        return res.json({
          authenticated: false
        });
      }

      const client =
        await ensureClient(req);

      const me =
        await client.getMe();

      res.json({
        authenticated: true,
        user: {
          id:
            me.id?.toString(),
          firstName:
            me.firstName || "",
          lastName:
            me.lastName || "",
          username:
            me.username || "",
          phone:
            me.phone || ""
        }
      });

    } catch (error) {
      req.session.telegramSession =
        null;

      res.json({
        authenticated: false
      });
    }
  }
);

/* ================================
   DIALOGS
================================ */

app.get(
  "/api/dialogs",
  async (req, res) => {
    try {
      const client =
        await ensureClient(req);

      const dialogs =
        await client.getDialogs({
          limit: 100
        });

      const result =
        dialogs.map(
          serializeDialog
        );

      res.json({
        success: true,
        dialogs: result
      });

    } catch (error) {
      res.status(401).json({
        success: false,
        message:
          formatError(error)
      });
    }
  }
);

/* ================================
   MESSAGES
================================ */

app.get(
  "/api/messages/:dialogId",
  async (req, res) => {
    try {
      const client =
        await ensureClient(req);

      const dialogId =
        req.params.dialogId;

      const limit =
        Math.min(
          Number(req.query.limit) ||
          50,
          100
        );

      const entity =
        await client.getEntity(
          dialogId
        );

      const messages =
        await client.getMessages(
          entity,
          {
            limit,
            reverse: true
          }
        );

      await client.markAsRead(
        entity
      );

      res.json({
        success: true,
        messages:
          messages.map(
            serializeMessage
          )
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        message:
          formatError(error)
      });
    }
  }
);

/* ================================
   SEND MESSAGE
================================ */

app.post(
  "/api/messages/:dialogId",
  async (req, res) => {
    try {
      const client =
        await ensureClient(req);

      const dialogId =
        req.params.dialogId;

      const text =
        String(
          req.body.message || ""
        ).trim();

      if (!text) {
        return res.status(400).json({
          success: false,
          message:
            "الرسالة فارغة"
        });
      }

      const entity =
        await client.getEntity(
          dialogId
        );

      const message =
        await client.sendMessage(
          entity,
          {
            message: text
          }
        );

      res.json({
        success: true,
        message:
          serializeMessage(message)
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        message:
          formatError(error)
      });
    }
  }
);

/* ================================
   SEND FILE
================================ */

app.post(
  "/api/upload/:dialogId",
  upload.single("file"),
  async (req, res) => {
    try {
      const client =
        await ensureClient(req);

      const dialogId =
        req.params.dialogId;

      if (!req.file) {
        return res.status(400).json({
          success: false,
          message:
            "لم يتم اختيار ملف"
        });
      }

      const entity =
        await client.getEntity(
          dialogId
        );

      const message =
        await client.sendFile(
          entity,
          {
            file: req.file.path,
            caption:
              req.body.caption || "",
            forceDocument: false
          }
        );

      fs.unlink(
        req.file.path,
        () => {}
      );

      res.json({
        success: true,
        message:
          serializeMessage(message)
      });

    } catch (error) {
      if (req.file?.path) {
        fs.unlink(
          req.file.path,
          () => {}
        );
      }

      res.status(500).json({
        success: false,
        message:
          formatError(error)
      });
    }
  }
);

/* ================================
   SEARCH
================================ */

app.get(
  "/api/search",
  async (req, res) => {
    try {
      const client =
        await ensureClient(req);

      const query =
        String(
          req.query.q || ""
        ).trim();

      if (!query) {
        return res.json({
          success: true,
          results: []
        });
      }

      const result =
        await client.invoke(
          new Api.contacts.Search({
            q: query,
            limit: 20
          })
        );

      const users =
        result.users.map(user => ({
          id:
            user.id?.toString(),
          name:
            getEntityName(user),
          username:
            user.username || "",
          type: "user"
        }));

      const chats =
        result.chats.map(chat => ({
          id:
            chat.id?.toString(),
          name:
            getEntityName(chat),
          username:
            chat.username || "",
          type: "chat"
        }));

      res.json({
        success: true,
        results: [
          ...users,
          ...chats
        ]
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        message:
          formatError(error)
      });
    }
  }
);

/* ================================
   LOGOUT
================================ */

app.post(
  "/api/logout",
  async (req, res) => {
    try {
      const client =
        clients.get(
          req.sessionID
        );

      if (client) {
        try {
          await client.disconnect();
        } catch {}
      }

      clients.delete(
        req.sessionID
      );

      req.session.destroy(() => {
        res.json({
          success: true
        });
      });

    } catch (error) {
      res.json({
        success: true
      });
    }
  }
);

/* ================================
   LIVE UPDATES
================================ */

function attachLiveUpdates(
  client,
  sessionId
) {
  if (client.__liveUpdatesAttached) {
    return;
  }

  client.__liveUpdatesAttached = true;

  client.addEventHandler(
    async event => {
      console.log(
        "New Telegram message",
        sessionId,
        event.message?.id
      );
    },
    new NewMessage({})
  );
}

app.use(
  express.static(
    path.join(
      __dirname,
      "public"
    )
  )
);

app.get(
  "*",
  (req, res) => {
    res.sendFile(
      path.join(
        __dirname,
        "public",
        "index.html"
      )
    );
  }
);

app.listen(
  PORT,
  () => {
    console.log(
      `Telegram Web running on port ${PORT}`
    );
  }
);
