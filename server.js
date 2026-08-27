import express from "express";
import session from "express-session";
import dotenv from "dotenv";
import multer from "multer";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

import { TelegramClient } from "telegram";
import { StringSession } from "telegram/sessions/index.js";
import { Api } from "telegram";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

const PORT = process.env.PORT || 3000;

const API_ID = Number(process.env.API_ID);
const API_HASH = process.env.API_HASH;

if (!API_ID || !API_HASH) {
  console.error("Missing Telegram API credentials");
  process.exit(1);
}

const uploadDir = path.join(
  __dirname,
  "uploads"
);

if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir);
}

app.use(
  express.json({
    limit: "10mb"
  })
);

app.use(
  express.urlencoded({
    extended: true
  })
);

app.use(
  session({
    secret:
      process.env.SESSION_SECRET ||
      "change-this-secret",
    resave: false,
    saveUninitialized: true,
    cookie: {
      secure: false,
      httpOnly: true,
      sameSite: "lax",
      maxAge:
        1000 *
        60 *
        60 *
        24 *
        30
    }
  })
);

const upload = multer({
  dest: uploadDir,
  limits: {
    fileSize:
      50 *
      1024 *
      1024
  }
});

const clients = new Map();

function errorMessage(error) {
  console.error(error);

  return (
    error?.errorMessage ||
    error?.message ||
    "حدث خطأ"
  );
}

function getClient(
  sessionId,
  savedSession = ""
) {
  if (clients.has(sessionId)) {
    return clients.get(sessionId);
  }

  const client =
    new TelegramClient(
      new StringSession(
        savedSession
      ),
      API_ID,
      API_HASH,
      {
        connectionRetries: 5
      }
    );

  clients.set(
    sessionId,
    client
  );

  return client;
}

async function requireClient(req) {
  if (
    !req.session.telegramSession
  ) {
    throw new Error(
      "UNAUTHORIZED"
    );
  }

  const client =
    getClient(
      req.sessionID,
      req.session
        .telegramSession
    );

  if (!client.connected) {
    await client.connect();
  }

  const authorized =
    await client.checkAuthorization();

  if (!authorized) {
    throw new Error(
      "UNAUTHORIZED"
    );
  }

  return client;
}

function cleanPhone(phone) {
  return String(phone || "")
    .replace(/[^\d+]/g, "")
    .trim();
}

function nameOf(entity) {
  if (!entity) {
    return "Telegram";
  }

  const name =
    `${entity.firstName || ""} ${
      entity.lastName || ""
    }`.trim();

  return (
    name ||
    entity.title ||
    entity.username ||
    "Telegram"
  );
}

function serializeMessage(message) {
  return {
    id:
      message.id,
    text:
      message.message || "",
    out:
      Boolean(message.out),
    date:
      message.date
        ? new Date(
            message.date
          ).toISOString()
        : null,
    media:
      Boolean(message.media),
    photo:
      Boolean(message.photo),
    document:
      Boolean(message.document)
  };
}

/* ===============================
   SEND LOGIN CODE
================================ */

app.post(
  "/api/auth/send-code",
  async (req, res) => {
    try {
      const phone =
        cleanPhone(
          req.body.phone
        );

      if (!phone) {
        return res.status(400).json({
          success: false,
          message:
            "أدخل رقم الهاتف"
        });
      }

      const client =
        getClient(
          req.sessionID
        );

      if (!client.connected) {
        await client.connect();
      }

      const result =
        await client.sendCode(
          {
            apiId:
              API_ID,
            apiHash:
              API_HASH
          },
          phone
        );

      req.session.loginPhone =
        phone;

      req.session.phoneCodeHash =
        result.phoneCodeHash;

      res.json({
        success: true
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        message:
          errorMessage(error)
      });
    }
  }
);

/* ===============================
   VERIFY CODE
================================ */

app.post(
  "/api/auth/verify-code",
  async (req, res) => {
    try {
      const phone =
        req.session.loginPhone;

      const phoneCodeHash =
        req.session.phoneCodeHash;

      const code =
        String(
          req.body.code || ""
        ).trim();

      if (
        !phone ||
        !phoneCodeHash
      ) {
        throw new Error(
          "اطلب رمزًا جديدًا"
        );
      }

      const client =
        getClient(
          req.sessionID
        );

      await client.invoke(
        new Api.auth.SignIn({
          phoneNumber:
            phone,
          phoneCodeHash,
          phoneCode:
            code
        })
      );

      req.session.telegramSession =
        client.session.save();

      req.session.loginPhone =
        null;

      req.session.phoneCodeHash =
        null;

      res.json({
        success: true
      });

    } catch (error) {
      const message =
        errorMessage(error);

      if (
        message.includes(
          "SESSION_PASSWORD_NEEDED"
        )
      ) {
        return res.status(401).json({
          success: false,
          passwordRequired: true
        });
      }

      res.status(500).json({
        success: false,
        message
      });
    }
  }
);

/* ===============================
   VERIFY PASSWORD
================================ */

app.post(
  "/api/auth/verify-password",
  async (req, res) => {
    try {
      const password =
        String(
          req.body.password || ""
        );

      const client =
        getClient(
          req.sessionID
        );

      await client.signInWithPassword(
        {
          apiId:
            API_ID,
          apiHash:
            API_HASH
        },
        {
          password:
            async () =>
              password,
          onError:
            async error => {
              throw error;
            }
        }
      );

      req.session.telegramSession =
        client.session.save();

      res.json({
        success: true
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        message:
          errorMessage(error)
      });
    }
  }
);

/* ===============================
   GET CURRENT USER
================================ */

app.get(
  "/api/me",
  async (req, res) => {
    try {
      const client =
        await requireClient(req);

      const me =
        await client.getMe();

      res.json({
        authenticated: true,
        user: {
          id:
            me.id?.toString(),
          name:
            nameOf(me),
          username:
            me.username || "",
          phone:
            me.phone || ""
        }
      });

    } catch {
      res.json({
        authenticated: false
      });
    }
  }
);

/* ===============================
   DIALOGS
================================ */

app.get(
  "/api/dialogs",
  async (req, res) => {
    try {
      const client =
        await requireClient(req);

      const dialogs =
        await client.getDialogs({
          limit: 100
        });

      res.json({
        success: true,
        dialogs:
          dialogs.map(
            dialog => ({
              id:
                dialog.entity.id.toString(),
              name:
                nameOf(
                  dialog.entity
                ),
              unread:
                dialog.unreadCount ||
                0,
              lastMessage:
                dialog.message
                  ?.message ||
                ""
            })
          )
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        message:
          errorMessage(error)
      });
    }
  }
);

/* ===============================
   MESSAGES
================================ */

app.get(
  "/api/messages/:id",
  async (req, res) => {
    try {
      const client =
        await requireClient(req);

      const entity =
        await client.getEntity(
          req.params.id
        );

      const messages =
        await client.getMessages(
          entity,
          {
            limit: 100,
            reverse: true
          }
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
          errorMessage(error)
      });
    }
  }
);

/* ===============================
   SEND MESSAGE
================================ */

app.post(
  "/api/messages/:id",
  async (req, res) => {
    try {
      const client =
        await requireClient(req);

      const text =
        String(
          req.body.text || ""
        ).trim();

      if (!text) {
        throw new Error(
          "الرسالة فارغة"
        );
      }

      const entity =
        await client.getEntity(
          req.params.id
        );

      const message =
        await client.sendMessage(
          entity,
          {
            message:
              text
          }
        );

      res.json({
        success: true,
        message:
          serializeMessage(
            message
          )
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        message:
          errorMessage(error)
      });
    }
  }
);

/* ===============================
   SEND FILE
================================ */

app.post(
  "/api/files/:id",
  upload.single("file"),
  async (req, res) => {
    try {
      const client =
        await requireClient(req);

      if (!req.file) {
        throw new Error(
          "اختر ملفًا"
        );
      }

      const entity =
        await client.getEntity(
          req.params.id
        );

      const message =
        await client.sendFile(
          entity,
          {
            file:
              req.file.path,
            caption:
              req.body.caption ||
              ""
          }
        );

      fs.unlink(
        req.file.path,
        () => {}
      );

      res.json({
        success: true,
        message:
          serializeMessage(
            message
          )
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        message:
          errorMessage(error)
      });
    }
  }
);

/* ===============================
   SEARCH
================================ */

app.get(
  "/api/search",
  async (req, res) => {
    try {
      const client =
        await requireClient(req);

      const query =
        String(
          req.query.q || ""
        ).trim();

      const result =
        await client.invoke(
          new Api.contacts.Search({
            q:
              query,
            limit:
              20
          })
        );

      const users =
        result.users.map(
          user => ({
            id:
              user.id.toString(),
            name:
              nameOf(user),
            username:
              user.username || ""
          })
        );

      const chats =
        result.chats.map(
          chat => ({
            id:
              chat.id.toString(),
            name:
              nameOf(chat),
            username:
              chat.username || ""
          })
        );

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
          errorMessage(error)
      });
    }
  }
);

/* ===============================
   LOGOUT
================================ */

app.post(
  "/api/logout",
  async (req, res) => {
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

    req.session.destroy(
      () => {
        res.json({
          success: true
        });
      }
    );
  }
);

app.use(
  express.static(
    path.join(
      __dirname,
      "public"
    )
  )
);

app.listen(
  PORT,
  () => {
    console.log(
      `Server running on port ${PORT}`
    );
  }
);
