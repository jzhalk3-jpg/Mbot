import express from "express";
import session from "express-session";
import dotenv from "dotenv";
import multer from "multer";
import fs from "fs";
import path from "path";
import crypto from "crypto";
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
  console.error("API_ID or API_HASH is missing");
  process.exit(1);
}

const uploadDir = path.join(__dirname, "uploads");

if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: true, limit: "50mb" }));

app.use(
  session({
    secret:
      process.env.SESSION_SECRET ||
      crypto.randomBytes(32).toString("hex"),
    resave: false,
    saveUninitialized: true,
    cookie: {
      httpOnly: true,
      sameSite: "lax",
      secure: false,
      maxAge: 1000 * 60 * 60 * 24 * 30
    }
  })
);

const upload = multer({
  dest: uploadDir,
  limits: {
    fileSize: 100 * 1024 * 1024
  }
});

/* =========================================
   CLIENT MANAGER (نفس الأصلي)
========================================= */

const clients = new Map();

function getClientKey(sessionId, accountId) {
  return `${sessionId}:${accountId}`;
}

function getClient(sessionId, accountId, sessionString = "") {
  const key = getClientKey(sessionId, accountId);

  if (clients.has(key)) {
    return clients.get(key);
  }

  const client = new TelegramClient(
    new StringSession(sessionString),
    API_ID,
    API_HASH,
    {
      connectionRetries: 5,
      autoReconnect: true
    }
  );

  clients.set(key, client);

  return client;
}

function getAccounts(req) {
  if (!Array.isArray(req.session.accounts)) {
    req.session.accounts = [];
  }

  return req.session.accounts;
}

function getActiveAccount(req) {
  const accounts = getAccounts(req);

  return accounts.find(
    account => account.id === req.session.activeAccountId
  );
}

async function requireClient(req) {
  const account = getActiveAccount(req);

  if (!account) {
    throw new Error("UNAUTHORIZED");
  }

  const client = getClient(
    req.sessionID,
    account.id,
    account.session
  );

  if (!client.connected) {
    await client.connect();
  }

  const authorized = await client.checkAuthorization();

  if (!authorized) {
    throw new Error("UNAUTHORIZED");
  }

  return {
    client,
    account
  };
}

/* =========================================
   HELPERS (نفس الأصلي مع إضافات)
========================================= */

function cleanPhone(phone) {
  return String(phone || "")
    .replace(/[^\d+]/g, "")
    .trim();
}

function errorMessage(error) {
  console.error(error);

  if (error?.errorMessage) {
    return error.errorMessage;
  }

  if (error?.message) {
    return error.message;
  }

  return "حدث خطأ غير متوقع";
}

function nameOf(entity) {
  if (!entity) return "Telegram";

  const name = `${entity.firstName || ""} ${entity.lastName || ""}`.trim();

  return (
    name ||
    entity.title ||
    entity.username ||
    "Telegram"
  );
}

function serializeUser(user) {
  return {
    id: user.id?.toString(),
    name: nameOf(user),
    username: user.username || "",
    phone: user.phone || "",
    premium: Boolean(user.premium)
  };
}

function serializeMessage(message) {
  return {
    id: message.id,
    text: message.message || "",
    out: Boolean(message.out),
    date: message.date
      ? new Date(message.date).toISOString()
      : null,
    media: Boolean(message.media),
    photo: Boolean(message.photo),
    document: Boolean(message.document),
    replyTo: message.replyTo?.replyToMsgId || null
  };
}

function saveSession(req) {
  return new Promise((resolve, reject) => {
    req.session.save(error => {
      if (error) reject(error);
      else resolve();
    });
  });
}

// دالة مساعدة لإرسال ملف من تيلجرام
async function downloadFile(client, messageId, entity) {
  const messages = await client.getMessages(entity, { ids: messageId });
  if (!messages || messages.length === 0) throw new Error("الرسالة غير موجودة");
  const msg = messages[0];
  if (!msg.media) throw new Error("لا يوجد ملف في هذه الرسالة");

  const buffer = await client.downloadMedia(msg.media);
  return buffer;
}

/* =========================================
   AUTH - SEND CODE (نفس الأصلي)
========================================= */

app.post("/api/auth/send-code", async (req, res) => {
  try {
    const phone = cleanPhone(req.body.phone);

    if (!phone) {
      return res.status(400).json({
        success: false,
        message: "أدخل رقم الهاتف"
      });
    }

    const loginId = crypto.randomUUID();

    const client = getClient(
      req.sessionID,
      `login-${loginId}`
    );

    if (!client.connected) {
      await client.connect();
    }

    const result = await client.sendCode(
      {
        apiId: API_ID,
        apiHash: API_HASH
      },
      phone
    );

    req.session.pendingLogin = {
      id: loginId,
      phone,
      phoneCodeHash: result.phoneCodeHash
    };

    await saveSession(req);

    res.json({
      success: true,
      message: "تم إرسال رمز التحقق"
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: errorMessage(error)
    });
  }
});

/* =========================================
   AUTH - VERIFY CODE (نفس الأصلي)
========================================= */

app.post("/api/auth/verify-code", async (req, res) => {
  try {
    const pending = req.session.pendingLogin;

    if (!pending) {
      throw new Error("اطلب رمز تسجيل جديد");
    }

    const code = String(req.body.code || "").trim();

    if (!code) {
      throw new Error("أدخل رمز التحقق");
    }

    const client = getClient(
      req.sessionID,
      `login-${pending.id}`
    );

    await client.invoke(
      new Api.auth.SignIn({
        phoneNumber: pending.phone,
        phoneCodeHash: pending.phoneCodeHash,
        phoneCode: code
      })
    );

    await finishLogin(req, client, pending.id);

    res.json({
      success: true,
      passwordRequired: false,
      accounts: getAccounts(req),
      activeAccountId: req.session.activeAccountId
    });

  } catch (error) {
    const message = errorMessage(error);

    if (message.includes("SESSION_PASSWORD_NEEDED")) {
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
});

/* =========================================
   AUTH - VERIFY 2FA (نفس الأصلي)
========================================= */

app.post("/api/auth/verify-password", async (req, res) => {
  try {
    const pending = req.session.pendingLogin;

    if (!pending) {
      throw new Error("انتهت جلسة تسجيل الدخول");
    }

    const password = String(req.body.password || "");

    if (!password) {
      throw new Error("أدخل كلمة المرور");
    }

    const client = getClient(
      req.sessionID,
      `login-${pending.id}`
    );

    if (!client.connected) {
      await client.connect();
    }

    await client.signInWithPassword(
      {
        apiId: API_ID,
        apiHash: API_HASH
      },
      {
        password: async () => password,
        onError: async error => {
          throw error;
        }
      }
    );

    await finishLogin(req, client, pending.id);

    res.json({
      success: true,
      accounts: getAccounts(req),
      activeAccountId: req.session.activeAccountId
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: errorMessage(error)
    });
  }
});

async function finishLogin(req, client, pendingId) {
  const me = await client.getMe();

  const accountId = me.id.toString();

  const accounts = getAccounts(req);

  const existingIndex = accounts.findIndex(
    account => account.id === accountId
  );

  const account = {
    id: accountId,
    name: nameOf(me),
    username: me.username || "",
    phone: me.phone || "",
    session: client.session.save()
  };

  if (existingIndex >= 0) {
    accounts[existingIndex] = account;
  } else {
    accounts.push(account);
  }

  req.session.activeAccountId = accountId;
  req.session.pendingLogin = null;

  clients.set(
    getClientKey(req.sessionID, accountId),
    client
  );

  clients.delete(
    getClientKey(req.sessionID, `login-${pendingId}`)
  );

  await saveSession(req);
}

/* =========================================
   CURRENT USER (نفس الأصلي)
========================================= */

app.get("/api/me", async (req, res) => {
  try {
    const { client, account } = await requireClient(req);

    const me = await client.getMe();

    res.json({
      authenticated: true,
      user: serializeUser(me),
      accountId: account.id,
      accounts: getAccounts(req).map(account => ({
        id: account.id,
        name: account.name,
        username: account.username,
        phone: account.phone
      }))
    });

  } catch {
    res.json({
      authenticated: false,
      accounts: []
    });
  }
});

/* =========================================
   MULTI ACCOUNTS (نفس الأصلي)
========================================= */

app.get("/api/accounts", (req, res) => {
  const accounts = getAccounts(req).map(account => ({
    id: account.id,
    name: account.name,
    username: account.username,
    phone: account.phone,
    active: account.id === req.session.activeAccountId
  }));

  res.json({
    success: true,
    accounts
  });
});

app.post("/api/accounts/switch", async (req, res) => {
  try {
    const accountId = String(req.body.accountId || "");

    const account = getAccounts(req).find(
      item => item.id === accountId
    );

    if (!account) {
      throw new Error("الحساب غير موجود");
    }

    const client = getClient(
      req.sessionID,
      account.id,
      account.session
    );

    if (!client.connected) {
      await client.connect();
    }

    const authorized = await client.checkAuthorization();

    if (!authorized) {
      throw new Error("انتهت جلسة الحساب");
    }

    req.session.activeAccountId = account.id;

    await saveSession(req);

    res.json({
      success: true,
      account: {
        id: account.id,
        name: account.name,
        username: account.username,
        phone: account.phone
      }
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: errorMessage(error)
    });
  }
});

app.post("/api/accounts/remove", async (req, res) => {
  try {
    const accountId = String(req.body.accountId || "");

    const accounts = getAccounts(req);

    const account = accounts.find(
      item => item.id === accountId
    );

    if (!account) {
      throw new Error("الحساب غير موجود");
    }

    const key = getClientKey(
      req.sessionID,
      accountId
    );

    const client = clients.get(key);

    if (client) {
      try {
        await client.disconnect();
      } catch {}

      clients.delete(key);
    }

    req.session.accounts = accounts.filter(
      item => item.id !== accountId
    );

    if (req.session.activeAccountId === accountId) {
      req.session.activeAccountId =
        req.session.accounts[0]?.id || null;
    }

    await saveSession(req);

    res.json({
      success: true,
      accounts: getAccounts(req)
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: errorMessage(error)
    });
  }
});

/* =========================================
   DIALOGS (محسّن مع تصفية)
========================================= */

app.get("/api/dialogs", async (req, res) => {
  try {
    const { client } = await requireClient(req);

    const limit = Math.min(
      Number(req.query.limit) || 100,
      200
    );

    const type = req.query.type; // 'user', 'group', 'channel'

    const dialogs = await client.getDialogs({
      limit
    });

    let filtered = dialogs;

    if (type === 'user') {
      filtered = dialogs.filter(d => d.entity.className?.includes('User'));
    } else if (type === 'group') {
      filtered = dialogs.filter(d => d.entity.megagroup || d.entity.group);
    } else if (type === 'channel') {
      filtered = dialogs.filter(d => d.entity.broadcast);
    }

    res.json({
      success: true,
      dialogs: filtered.map(dialog => ({
        id: dialog.entity.id.toString(),
        name: nameOf(dialog.entity),
        unread: dialog.unreadCount || 0,
        lastMessage:
          dialog.message?.message ||
          "",
        username:
          dialog.entity.username || "",
        isUser:
          Boolean(dialog.entity.className?.includes("User")),
        isChannel:
          Boolean(dialog.entity.broadcast),
        isGroup:
          Boolean(dialog.entity.megagroup)
      }))
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: errorMessage(error)
    });
  }
});

/* =========================================
   MESSAGES (نفس الأصلي مع حذف وتحرير وتثبيت)
========================================= */

app.get("/api/messages/:id", async (req, res) => {
  try {
    const { client } = await requireClient(req);

    const entity = await client.getEntity(
      req.params.id
    );

    const messages = await client.getMessages(
      entity,
      {
        limit: Math.min(
          Number(req.query.limit) || 100,
          200
        ),
        reverse: true
      }
    );

    res.json({
      success: true,
      messages: messages.map(serializeMessage)
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: errorMessage(error)
    });
  }
});

app.post("/api/messages/:id", async (req, res) => {
  try {
    const { client } = await requireClient(req);

    const text = String(req.body.text || "").trim();

    if (!text) {
      throw new Error("الرسالة فارغة");
    }

    const entity = await client.getEntity(
      req.params.id
    );

    const options = {
      message: text
    };

    if (req.body.replyTo) {
      options.replyTo = Number(req.body.replyTo);
    }

    const message = await client.sendMessage(
      entity,
      options
    );

    res.json({
      success: true,
      message: serializeMessage(message)
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: errorMessage(error)
    });
  }
});

// حذف رسالة
app.delete("/api/messages/:chatId/:msgId", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.chatId);
    await client.deleteMessages(entity, [Number(req.params.msgId)]);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// تحرير رسالة
app.put("/api/messages/:chatId/:msgId", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.chatId);
    const newText = String(req.body.text || "").trim();
    if (!newText) throw new Error("النص مطلوب");
    await client.editMessage(entity, { message: newText, id: Number(req.params.msgId) });
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// تثبيت رسالة
app.post("/api/messages/:chatId/:msgId/pin", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.chatId);
    await client.pinMessage(entity, { id: Number(req.params.msgId) });
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// إلغاء تثبيت رسالة
app.delete("/api/messages/:chatId/:msgId/pin", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.chatId);
    await client.unpinMessage(entity, { id: Number(req.params.msgId) });
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// إرسال تفاعل (ريأكشن)
app.post("/api/messages/:chatId/:msgId/reaction", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.chatId);
    const reaction = req.body.reaction; // مثلاً "👍" أو "❤️"
    if (!reaction) throw new Error("التفاعل مطلوب");
    // استخدم Api.messages.SendReaction
    await client.invoke(
      new Api.messages.SendReaction({
        peer: entity,
        msgId: Number(req.params.msgId),
        reaction: [new Api.ReactionEmoji({ emoticon: reaction })]
      })
    );
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

/* =========================================
   FILES (نفس الأصلي مع إرسال أنواع متعددة)
========================================= */

app.post(
  "/api/files/:id",
  upload.single("file"),
  async (req, res) => {
    try {
      const { client } = await requireClient(req);

      if (!req.file) {
        throw new Error("اختر ملفًا");
      }

      const entity = await client.getEntity(
        req.params.id
      );

      // تحديد نوع الملف حسب الـ mime أو الامتداد
      const filePath = req.file.path;
      const message = await client.sendFile(
        entity,
        {
          file: filePath,
          caption: req.body.caption || "",
          // يمكن إضافة forceDocument: true لإرساله كمستند
        }
      );

      fs.unlink(req.file.path, () => {});

      res.json({
        success: true,
        message: serializeMessage(message)
      });

    } catch (error) {
      if (req.file?.path) {
        fs.unlink(req.file.path, () => {});
      }

      res.status(500).json({
        success: false,
        message: errorMessage(error)
      });
    }
  }
);

// إرسال صوت (Voice)
app.post("/api/messages/:id/voice", upload.single("voice"), async (req, res) => {
  try {
    const { client } = await requireClient(req);
    if (!req.file) throw new Error("اختر ملف صوتي");
    const entity = await client.getEntity(req.params.id);
    const msg = await client.sendVoice(entity, {
      file: req.file.path,
      caption: req.body.caption || ""
    });
    fs.unlink(req.file.path, () => {});
    res.json({ success: true, message: serializeMessage(msg) });
  } catch (error) {
    if (req.file?.path) fs.unlink(req.file.path, () => {});
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// إرسال فيديو
app.post("/api/messages/:id/video", upload.single("video"), async (req, res) => {
  try {
    const { client } = await requireClient(req);
    if (!req.file) throw new Error("اختر ملف فيديو");
    const entity = await client.getEntity(req.params.id);
    const msg = await client.sendVideo(entity, {
      file: req.file.path,
      caption: req.body.caption || ""
    });
    fs.unlink(req.file.path, () => {});
    res.json({ success: true, message: serializeMessage(msg) });
  } catch (error) {
    if (req.file?.path) fs.unlink(req.file.path, () => {});
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// إرسال مستند
app.post("/api/messages/:id/document", upload.single("document"), async (req, res) => {
  try {
    const { client } = await requireClient(req);
    if (!req.file) throw new Error("اختر ملفاً");
    const entity = await client.getEntity(req.params.id);
    const msg = await client.sendDocument(entity, {
      file: req.file.path,
      caption: req.body.caption || "",
      // forceDocument: true
    });
    fs.unlink(req.file.path, () => {});
    res.json({ success: true, message: serializeMessage(msg) });
  } catch (error) {
    if (req.file?.path) fs.unlink(req.file.path, () => {});
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// إرسال ستيكر (يحتاج أن يكون ملف بصيغة webp)
app.post("/api/messages/:id/sticker", upload.single("sticker"), async (req, res) => {
  try {
    const { client } = await requireClient(req);
    if (!req.file) throw new Error("اختر ملف ستيكر");
    const entity = await client.getEntity(req.params.id);
    const msg = await client.sendSticker(entity, {
      file: req.file.path,
      caption: req.body.caption || ""
    });
    fs.unlink(req.file.path, () => {});
    res.json({ success: true, message: serializeMessage(msg) });
  } catch (error) {
    if (req.file?.path) fs.unlink(req.file.path, () => {});
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// إرسال جهة اتصال
app.post("/api/messages/:id/contact", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const { phone, firstName, lastName } = req.body;
    if (!phone || !firstName) throw new Error("رقم الهاتف والاسم الأول مطلوبان");
    const entity = await client.getEntity(req.params.id);
    const msg = await client.sendContact(entity, {
      phoneNumber: phone,
      firstName: firstName,
      lastName: lastName || ""
    });
    res.json({ success: true, message: serializeMessage(msg) });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// إرسال موقع
app.post("/api/messages/:id/location", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const { latitude, longitude } = req.body;
    if (latitude == null || longitude == null) throw new Error("الإحداثيات مطلوبة");
    const entity = await client.getEntity(req.params.id);
    const msg = await client.sendLocation(entity, {
      latitude: parseFloat(latitude),
      longitude: parseFloat(longitude)
    });
    res.json({ success: true, message: serializeMessage(msg) });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// تحميل ملف من رسالة
app.get("/api/files/:chatId/:msgId", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.chatId);
    const buffer = await downloadFile(client, Number(req.params.msgId), entity);
    res.setHeader('Content-Disposition', 'attachment; filename="file"');
    res.send(buffer);
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

/* =========================================
   CHAT / CHANNEL / GROUP MANAGEMENT
========================================= */

// جلب معلومات المحادثة
app.get("/api/chat/:id", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.id);
    const full = await client.invoke(new Api.messages.GetFullChat({
      chatId: entity.id
    })); // قد لا يعمل مع القنوات، نستخدم getFullChannel للقنوات
    // نستخدم طريقة بديلة
    let info;
    if (entity.broadcast) {
      const ch = await client.invoke(new Api.channels.GetFullChannel({ channel: entity }));
      info = ch.fullChat;
    } else if (entity.megagroup) {
      const ch = await client.invoke(new Api.channels.GetFullChannel({ channel: entity }));
      info = ch.fullChat;
    } else {
      const ch = await client.invoke(new Api.messages.GetFullChat({ chatId: entity.id }));
      info = ch.fullChat;
    }
    res.json({
      success: true,
      id: entity.id.toString(),
      name: nameOf(entity),
      username: entity.username || "",
      about: info?.about || "",
      participantsCount: info?.participantsCount || 0,
      isChannel: Boolean(entity.broadcast),
      isGroup: Boolean(entity.megagroup)
    });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// إنشاء قناة أو مجموعة
app.post("/api/channels/create", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const { title, about, type } = req.body; // type: 'group', 'channel', 'supergroup'
    if (!title) throw new Error("العنوان مطلوب");
    let result;
    if (type === 'channel') {
      result = await client.invoke(new Api.channels.CreateChannel({
        title,
        about: about || "",
        broadcast: true,
        megagroup: false
      }));
    } else if (type === 'supergroup') {
      result = await client.invoke(new Api.channels.CreateChannel({
        title,
        about: about || "",
        broadcast: false,
        megagroup: true
      }));
    } else { // group عادي
      result = await client.invoke(new Api.messages.CreateChat({
        title,
        users: [] // يمكن إضافة أعضاء لاحقاً
      }));
    }
    res.json({ success: true, chat: result });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// تحديث معلومات المحادثة (الاسم، الوصف، الصورة)
app.put("/api/chat/:id", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.id);
    const { name, about } = req.body;
    if (name) {
      await client.invoke(new Api.channels.EditTitle({ channel: entity, title: name }));
    }
    if (about) {
      await client.invoke(new Api.channels.EditAbout({ channel: entity, about }));
    }
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// تغيير صورة المحادثة
app.post("/api/chat/:id/photo", upload.single("photo"), async (req, res) => {
  try {
    const { client } = await requireClient(req);
    if (!req.file) throw new Error("اختر صورة");
    const entity = await client.getEntity(req.params.id);
    await client.invoke(new Api.channels.EditPhoto({
      channel: entity,
      photo: await client.uploadFile({ file: req.file.path })
    }));
    fs.unlink(req.file.path, () => {});
    res.json({ success: true });
  } catch (error) {
    if (req.file?.path) fs.unlink(req.file.path, () => {});
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// حذف قناة/مجموعة (فقط للقنوات والمجموعات الفائقة)
app.delete("/api/chat/:id", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.id);
    if (entity.broadcast || entity.megagroup) {
      await client.invoke(new Api.channels.DeleteChannel({ channel: entity }));
    } else {
      await client.invoke(new Api.messages.DeleteChat({ chatId: entity.id }));
    }
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

/* =========================================
   MEMBERS MANAGEMENT
========================================= */

// جلب قائمة الأعضاء
app.get("/api/chat/:id/members", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.id);
    const participants = await client.getParticipants(entity, {
      limit: Math.min(Number(req.query.limit) || 100, 200)
    });
    res.json({
      success: true,
      members: participants.map(p => ({
        id: p.id.toString(),
        name: nameOf(p),
        username: p.username || "",
        isAdmin: Boolean(p.participant?.adminRights),
        isOwner: Boolean(p.participant?.isCreator)
      }))
    });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// طرد عضو
app.post("/api/chat/:id/kick", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.id);
    const userId = req.body.userId;
    if (!userId) throw new Error("معرف المستخدم مطلوب");
    const user = await client.getEntity(userId);
    await client.kickParticipant(entity, user);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// حظر عضو
app.post("/api/chat/:id/ban", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.id);
    const userId = req.body.userId;
    if (!userId) throw new Error("معرف المستخدم مطلوب");
    const user = await client.getEntity(userId);
    await client.banParticipant(entity, user);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// إلغاء حظر
app.post("/api/chat/:id/unban", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.id);
    const userId = req.body.userId;
    if (!userId) throw new Error("معرف المستخدم مطلوب");
    const user = await client.getEntity(userId);
    await client.unbanParticipant(entity, user);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// رفع مشرف
app.post("/api/chat/:id/promote", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.id);
    const userId = req.body.userId;
    if (!userId) throw new Error("معرف المستخدم مطلوب");
    const user = await client.getEntity(userId);
    // تعيين صلاحيات مشرف (كل الصلاحيات)
    const rights = new Api.ChatAdminRights({
      changeInfo: true,
      postMessages: true,
      editMessages: true,
      deleteMessages: true,
      banUsers: true,
      inviteUsers: true,
      pinMessages: true,
      addAdmins: true,
      anonymous: false,
      manageCall: true,
      other: true
    });
    await client.invoke(new Api.channels.EditAdmin({
      channel: entity,
      userId: user.id,
      adminRights: rights,
      rank: req.body.rank || "admin"
    }));
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// خفض مشرف
app.post("/api/chat/:id/demote", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.id);
    const userId = req.body.userId;
    if (!userId) throw new Error("معرف المستخدم مطلوب");
    const user = await client.getEntity(userId);
    await client.invoke(new Api.channels.EditAdmin({
      channel: entity,
      userId: user.id,
      adminRights: new Api.ChatAdminRights({})
    }));
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

// إنشاء رابط دعوة
app.post("/api/chat/:id/invite", async (req, res) => {
  try {
    const { client } = await requireClient(req);
    const entity = await client.getEntity(req.params.id);
    const link = await client.invoke(new Api.messages.ExportChatInvite({
      peer: entity,
      // يمكن إضافة expireDate, usageLimit
    }));
    res.json({ success: true, link: link.link });
  } catch (error) {
    res.status(500).json({ success: false, message: errorMessage(error) });
  }
});

/* =========================================
   SEARCH (نفس الأصلي مع إضافة نوع)
========================================= */

app.get("/api/search", async (req, res) => {
  try {
    const { client } = await requireClient(req);

    const query = String(
      req.query.q || ""
    ).trim();

    if (!query) {
      return res.json({
        success: true,
        results: []
      });
    }

    const result = await client.invoke(
      new Api.contacts.Search({
        q: query,
        limit: 30
      })
    );

    const users = (result.users || []).map(
      user => ({
        id: user.id.toString(),
        name: nameOf(user),
        username: user.username || "",
        type: "user"
      })
    );

    const chats = (result.chats || []).map(
      chat => ({
        id: chat.id.toString(),
        name: nameOf(chat),
        username: chat.username || "",
        type: "chat"
      })
    );

    res.json({
      success: true,
      results: [...users, ...chats]
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: errorMessage(error)
    });
  }
});

/* =========================================
   PROFILE (نفس الأصلي)
========================================= */

app.get("/api/profile", async (req, res) => {
  try {
    const { client } = await requireClient(req);

    const me = await client.getMe();

    res.json({
      success: true,
      profile: serializeUser(me)
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: errorMessage(error)
    });
  }
});

app.post("/api/profile", async (req, res) => {
  try {
    const { client } = await requireClient(req);

    await client.invoke(
      new Api.account.UpdateProfile({
        firstName:
          req.body.firstName || undefined,
        lastName:
          req.body.lastName || undefined,
        about:
          req.body.about || undefined
      })
    );

    const me = await client.getMe();

    res.json({
      success: true,
      profile: serializeUser(me)
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: errorMessage(error)
    });
  }
});

/* =========================================
   LOGOUT (نفس الأصلي)
========================================= */

app.post("/api/logout", async (req, res) => {
  try {
    const accounts = getAccounts(req);

    for (const account of accounts) {
      const key = getClientKey(
        req.sessionID,
        account.id
      );

      const client = clients.get(key);

      if (client) {
        try {
          await client.disconnect();
        } catch {}

        clients.delete(key);
      }
    }

    req.session.destroy(() => {
      res.json({
        success: true
      });
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      message: errorMessage(error)
    });
  }
});

/* =========================================
   HEALTH (نفس الأصلي)
========================================= */

app.get("/api/health", (req, res) => {
  res.json({
    success: true,
    status: "online"
  });
});

/* =========================================
   STATIC WEBSITE (نفس الأصلي)
========================================= */

app.use(
  express.static(
    path.join(
      __dirname,
      "public"
    )
  )
);

app.get("*", (req, res) => {
  res.sendFile(
    path.join(
      __dirname,
      "public",
      "index.html"
    )
  );
});

/* =========================================
   START
========================================= */

app.listen(PORT, () => {
  console.log(
    `Telegram Web Server running on port ${PORT}`
  );
});
