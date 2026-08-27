const loginPage =
  document.getElementById("loginPage");

const appPage =
  document.getElementById("appPage");

const phoneStep =
  document.getElementById("phoneStep");

const codeStep =
  document.getElementById("codeStep");

const passwordStep =
  document.getElementById("passwordStep");

const phoneInput =
  document.getElementById("phoneInput");

const codeInput =
  document.getElementById("codeInput");

const passwordInput =
  document.getElementById("passwordInput");

const sendCodeBtn =
  document.getElementById("sendCodeBtn");

const verifyCodeBtn =
  document.getElementById("verifyCodeBtn");

const verifyPasswordBtn =
  document.getElementById(
    "verifyPasswordBtn"
  );

const backBtn =
  document.getElementById("backBtn");

const statusBox =
  document.getElementById("status");

const dialogsList =
  document.getElementById("dialogsList");

const searchInput =
  document.getElementById("searchInput");

const searchResults =
  document.getElementById(
    "searchResults"
  );

const chatEmpty =
  document.getElementById("chatEmpty");

const chatWindow =
  document.getElementById("chatWindow");

const chatHeader =
  document.getElementById("chatHeader");

const messagesBox =
  document.getElementById("messages");

const messageInput =
  document.getElementById(
    "messageInput"
  );

const sendMessageBtn =
  document.getElementById(
    "sendMessageBtn"
  );

const fileInput =
  document.getElementById("fileInput");

const userBox =
  document.getElementById("userBox");

const profileBtn =
  document.getElementById("profileBtn");

const profileModal =
  document.getElementById(
    "profileModal"
  );

const closeProfileBtn =
  document.getElementById(
    "closeProfileBtn"
  );

const profileContent =
  document.getElementById(
    "profileContent"
  );

const logoutBtn =
  document.getElementById("logoutBtn");

let currentDialog = null;

let currentUser = null;

let allDialogs = [];

function setStatus(
  text,
  success = false
) {
  statusBox.textContent = text;

  statusBox.style.color =
    success
      ? "#2e7d32"
      : "#e53935";
}

function showLogin() {
  appPage.classList.add(
    "hidden"
  );

  loginPage.classList.remove(
    "hidden"
  );

  phoneStep.classList.remove(
    "hidden"
  );

  codeStep.classList.add(
    "hidden"
  );

  passwordStep.classList.add(
    "hidden"
  );
}

function showApp() {
  loginPage.classList.add(
    "hidden"
  );

  appPage.classList.remove(
    "hidden"
  );
}

async function api(
  url,
  options = {}
) {
  const response =
    await fetch(
      url,
      options
    );

  return response.json();
}

/* ==========================
   SEND CODE
========================== */

sendCodeBtn.addEventListener(
  "click",
  async () => {

    const phone =
      phoneInput.value.trim();

    if (!phone) {
      return setStatus(
        "أدخل رقم الهاتف"
      );
    }

    try {

      sendCodeBtn.disabled =
        true;

      sendCodeBtn.textContent =
        "جاري الإرسال...";

      setStatus("");

      const data =
        await api(
          "/api/auth/send-code",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body:
              JSON.stringify({
                phone
              })
          }
        );

      if (!data.success) {
        throw new Error(
          data.message
        );
      }

      phoneStep.classList.add(
        "hidden"
      );

      codeStep.classList.remove(
        "hidden"
      );

      setStatus(
        "تم إرسال رمز التحقق",
        true
      );

    } catch (error) {

      setStatus(
        error.message
      );

    } finally {

      sendCodeBtn.disabled =
        false;

      sendCodeBtn.textContent =
        "متابعة";
    }

  }
);

/* ==========================
   VERIFY CODE
========================== */

verifyCodeBtn.addEventListener(
  "click",
  async () => {

    const code =
      codeInput.value.trim();

    if (!code) {
      return setStatus(
        "أدخل رمز التحقق"
      );
    }

    try {

      verifyCodeBtn.disabled =
        true;

      const data =
        await api(
          "/api/auth/verify-code",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body:
              JSON.stringify({
                code
              })
          }
        );

      if (
        data.passwordRequired
      ) {
        codeStep.classList.add(
          "hidden"
        );

        passwordStep.classList.remove(
          "hidden"
        );

        return;
      }

      if (!data.success) {
        throw new Error(
          data.message
        );
      }

      await startApp();

    } catch (error) {

      setStatus(
        error.message
      );

    } finally {

      verifyCodeBtn.disabled =
        false;
    }

  }
);

/* ==========================
   VERIFY 2FA
========================== */

verifyPasswordBtn.addEventListener(
  "click",
  async () => {

    const password =
      passwordInput.value;

    if (!password) {
      return setStatus(
        "أدخل كلمة المرور"
      );
    }

    try {

      const data =
        await api(
          "/api/auth/verify-password",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body:
              JSON.stringify({
                password
              })
          }
        );

      if (!data.success) {
        throw new Error(
          data.message
        );
      }

      await startApp();

    } catch (error) {

      setStatus(
        error.message
      );
    }

  }
);

backBtn.addEventListener(
  "click",
  () => {

    codeStep.classList.add(
      "hidden"
    );

    phoneStep.classList.remove(
      "hidden"
    );

    setStatus("");
  }
);

/* ==========================
   START APP
========================== */

async function startApp() {

  const data =
    await api("/api/me");

  if (!data.authenticated) {
    return showLogin();
  }

  currentUser =
    data.user;

  showApp();

  renderUser();

  await loadDialogs();
}

/* ==========================
   USER
========================== */

function renderUser() {

  const name =
    `${currentUser.firstName || ""} ${
      currentUser.lastName || ""
    }`.trim();

  userBox.textContent =
    `مرحبًا ${name || "مستخدم Telegram"}`;
}

/* ==========================
   DIALOGS
========================== */

async function loadDialogs() {

  dialogsList.innerHTML =
    "<p style='padding:20px'>جاري التحميل...</p>";

  try {

    const data =
      await api(
        "/api/dialogs"
      );

    if (!data.success) {
      throw new Error(
        data.message
      );
    }

    allDialogs =
      data.dialogs;

    renderDialogs(
      allDialogs
    );

  } catch (error) {

    dialogsList.innerHTML =
      "<p style='padding:20px'>تعذر تحميل المحادثات</p>";
  }
}

function renderDialogs(dialogs) {

  if (!dialogs.length) {
    dialogsList.innerHTML =
      "<p style='padding:20px'>لا توجد محادثات</p>";

    return;
  }

  dialogsList.innerHTML =
    dialogs.map(
      dialog => {

        const initial =
          (dialog.name || "T")
            .charAt(0)
            .toUpperCase();

        const unread =
          dialog.unreadCount > 0
            ? `
              <div class="unread">
                ${dialog.unreadCount}
              </div>
              `
            : "";

        return `
        <div
        class="dialog"
        data-id="${dialog.id}"
        data-name="${escapeHtml(
          dialog.name
        )}"
        >

          <div class="dialog-avatar">
            ${initial}
          </div>

          <div class="dialog-main">

            <div class="dialog-name">
              ${escapeHtml(
                dialog.name
              )}
            </div>

            <div class="dialog-last">
              ${escapeHtml(
                dialog.lastMessage ||
                ""
              )}
            </div>

          </div>

          ${unread}

        </div>
        `;
      }
    ).join("");

  document
    .querySelectorAll(".dialog")
    .forEach(
      element => {

        element.addEventListener(
          "click",
          () => {

            openChat(
              element.dataset.id,
              element.dataset.name
            );

          }
        );
      }
    );
}

/* ==========================
   OPEN CHAT
========================== */

async function openChat(
  id,
  name
) {

  currentDialog = {
    id,
    name
  };

  chatEmpty.classList.add(
    "hidden"
  );

  chatWindow.classList.remove(
    "hidden"
  );

  chatHeader.textContent =
    name;

  messagesBox.innerHTML =
    "<p>جاري تحميل الرسائل...</p>";

  try {

    const data =
      await api(
        `/api/messages/${encodeURIComponent(
          id
        )}`
      );

    if (!data.success) {
      throw new Error(
        data.message
      );
    }

    renderMessages(
      data.messages
    );

  } catch (error) {

    messagesBox.innerHTML =
      "<p>تعذر تحميل الرسائل</p>";
  }
}

/* ==========================
   MESSAGES
========================== */

function renderMessages(messages) {

  messagesBox.innerHTML = "";

  messages.forEach(
    message => {

      appendMessage(
        message
      );

    }
  );

  scrollMessages();
}

function appendMessage(
  message
) {

  const element =
    document.createElement("div");

  element.className =
    "message" +
    (
      message.out
        ? " out"
        : ""
    );

  let content =
    "";

  if (message.message) {
    content =
      escapeHtml(
        message.message
      );
  }

  if (message.photo) {
    content +=
      "<div class='file-message'>📷 صورة</div>";
  }

  if (message.document) {
    content +=
      `<div class='file-message'>
        📎 ${
          escapeHtml(
            message.fileName ||
            "ملف"
          )
        }
      </div>`;
  }

  const date =
    message.date
      ? new Date(
          message.date
        ).toLocaleTimeString(
          "ar"
        )
      : "";

  element.innerHTML =
    `
    <div>
      ${content}
    </div>

    <span class="message-time">
      ${date}
    </span>
    `;

  messagesBox.appendChild(
    element
  );
}

function scrollMessages() {

  messagesBox.scrollTop =
    messagesBox.scrollHeight;
}

/* ==========================
   SEND TEXT
========================== */

sendMessageBtn.addEventListener(
  "click",
  sendMessage
);

messageInput.addEventListener(
  "keydown",
  event => {

    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      sendMessage();
    }
  }
);

async function sendMessage() {

  if (!currentDialog) {
    return;
  }

  const message =
    messageInput.value.trim();

  if (!message) {
    return;
  }

  messageInput.value = "";

  try {

    const data =
      await api(
        `/api/messages/${encodeURIComponent(
          currentDialog.id
        )}`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body:
            JSON.stringify({
              message
            })
        }
      );

    if (!data.success) {
      throw new Error(
        data.message
      );
    }

    appendMessage(
      data.message
    );

    scrollMessages();

  } catch (error) {

    alert(
      error.message ||
      "فشل إرسال الرسالة"
    );
  }
}

/* ==========================
   UPLOAD FILE
========================== */

fileInput.addEventListener(
  "change",
  async () => {

    if (
      !currentDialog ||
      !fileInput.files.length
    ) {
      return;
    }

    const file =
      fileInput.files[0];

    const formData =
      new FormData();

    formData.append(
      "file",
      file
    );

    try {

      const response =
        await fetch(
          `/api/upload/${encodeURIComponent(
            currentDialog.id
          )}`,
          {
            method: "POST",
            body: formData
          }
        );

      const data =
        await response.json();

      if (!data.success) {
        throw new Error(
          data.message
        );
      }

      appendMessage(
        data.message
      );

      scrollMessages();

    } catch (error) {

      alert(
        error.message ||
        "فشل رفع الملف"
      );

    } finally {

      fileInput.value = "";
    }

  }
);

/* ==========================
   SEARCH
========================== */

let searchTimer;

searchInput.addEventListener(
  "input",
  () => {

    clearTimeout(
      searchTimer
    );

    const query =
      searchInput.value.trim();

    if (!query) {

      searchResults.classList.add(
        "hidden"
      );

      return;
    }

    searchTimer =
      setTimeout(
        () =>
          searchTelegram(
            query
          ),
        400
      );

  }
);

async function searchTelegram(
  query
) {

  try {

    const data =
      await api(
        `/api/search?q=${encodeURIComponent(
          query
        )}`
      );

    if (!data.success) {
      return;
    }

    searchResults.innerHTML =
      data.results.map(
        result =>
          `
          <div
          class="search-result"
          data-id="${result.id}"
          data-name="${escapeHtml(
            result.name
          )}"
          >

            <strong>
              ${escapeHtml(
                result.name
              )}
            </strong>

            <br>

            <small>
              ${
                result.username
                  ? "@" +
                    escapeHtml(
                      result.username
                    )
                  : ""
              }
            </small>

          </div>
          `
      ).join("");

    searchResults.classList.remove(
      "hidden"
    );

    document
      .querySelectorAll(
        ".search-result"
      )
      .forEach(
        element => {

          element.addEventListener(
            "click",
            () => {

              searchResults.classList.add(
                "hidden"
              );

              searchInput.value = "";

              openChat(
                element.dataset.id,
                element.dataset.name
              );
            }
          );
        }
      );

  } catch {}
}

/* ==========================
   PROFILE
========================== */

profileBtn.addEventListener(
  "click",
  () => {

    const name =
      `${currentUser.firstName || ""} ${
        currentUser.lastName || ""
      }`.trim();

    profileContent.innerHTML =
      `
      <p><strong>الاسم:</strong> ${
        escapeHtml(name)
      }</p>

      <br>

      <p><strong>المعرف:</strong>
        ${
          currentUser.username
            ? "@" +
              escapeHtml(
                currentUser.username
              )
            : "لا يوجد"
        }
      </p>

      <br>

      <p><strong>رقم الهاتف:</strong>
        ${
          escapeHtml(
            currentUser.phone ||
            ""
          )
        }
      </p>
      `;

    profileModal.classList.remove(
      "hidden"
    );
  }
);

closeProfileBtn.addEventListener(
  "click",
  () => {

    profileModal.classList.add(
      "hidden"
    );

  }
);

/* ==========================
   LOGOUT
========================== */

logoutBtn.addEventListener(
  "click",
  async () => {

    await api(
      "/api/logout",
      {
        method: "POST"
      }
    );

    currentUser = null;

    currentDialog = null;

    profileModal.classList.add(
      "hidden"
    );

    showLogin();

  }
);

/* ==========================
   ESCAPE HTML
========================== */

function escapeHtml(text) {

  const div =
    document.createElement("div");

  div.textContent =
    text || "";

  return div.innerHTML;
}

/* ==========================
   CHECK LOGIN
========================== */

async function init() {

  try {

    const data =
      await api("/api/me");

    if (data.authenticated) {

      currentUser =
        data.user;

      showApp();

      renderUser();

      await loadDialogs();

    } else {

      showLogin();
    }

  } catch {

    showLogin();
  }
}

init();
