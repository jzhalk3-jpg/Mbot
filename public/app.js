const loginPage =
  document.getElementById(
    "loginPage"
  );

const appPage =
  document.getElementById(
    "appPage"
  );

const phoneStep =
  document.getElementById(
    "phoneStep"
  );

const codeStep =
  document.getElementById(
    "codeStep"
  );

const passwordStep =
  document.getElementById(
    "passwordStep"
  );

const phoneInput =
  document.getElementById(
    "phoneInput"
  );

const codeInput =
  document.getElementById(
    "codeInput"
  );

const passwordInput =
  document.getElementById(
    "passwordInput"
  );

const status =
  document.getElementById(
    "status"
  );

const dialogs =
  document.getElementById(
    "dialogs"
  );

const searchInput =
  document.getElementById(
    "searchInput"
  );

const emptyChat =
  document.getElementById(
    "emptyChat"
  );

const chatPage =
  document.getElementById(
    "chatPage"
  );

const chatHeader =
  document.getElementById(
    "chatHeader"
  );

const messages =
  document.getElementById(
    "messages"
  );

const messageInput =
  document.getElementById(
    "messageInput"
  );

const fileInput =
  document.getElementById(
    "fileInput"
  );

const settingsModal =
  document.getElementById(
    "settingsModal"
  );

let currentDialog =
  null;

let currentUser =
  null;

let dialogList =
  [];

function setStatus(text) {
  status.textContent =
    text || "";
}

async function request(
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

function showLogin() {
  appPage.classList.add(
    "hidden"
  );

  loginPage.classList.remove(
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

/* LOGIN */

document
  .getElementById(
    "sendCodeBtn"
  )
  .onclick =
  async () => {

    try {

      const data =
        await request(
          "/api/auth/send-code",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body:
              JSON.stringify({
                phone:
                  phoneInput.value
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
        "تم إرسال رمز التحقق"
      );

    } catch (error) {

      setStatus(
        error.message
      );
    }
  };

document
  .getElementById(
    "verifyCodeBtn"
  )
  .onclick =
  async () => {

    try {

      const data =
        await request(
          "/api/auth/verify-code",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body:
              JSON.stringify({
                code:
                  codeInput.value
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

      startApp();

    } catch (error) {

      setStatus(
        error.message
      );
    }
  };

document
  .getElementById(
    "verifyPasswordBtn"
  )
  .onclick =
  async () => {

    try {

      const data =
        await request(
          "/api/auth/verify-password",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body:
              JSON.stringify({
                password:
                  passwordInput.value
              })
          }
        );

      if (!data.success) {
        throw new Error(
          data.message
        );
      }

      startApp();

    } catch (error) {

      setStatus(
        error.message
      );
    }
  };

/* START */

async function startApp() {

  const data =
    await request(
      "/api/me"
    );

  if (!data.authenticated) {
    return showLogin();
  }

  currentUser =
    data.user;

  showApp();

  loadDialogs();
}

/* DIALOGS */

async function loadDialogs() {

  dialogs.innerHTML =
    "جاري تحميل المحادثات...";

  const data =
    await request(
      "/api/dialogs"
    );

  if (!data.success) {
    dialogs.innerHTML =
      "حدث خطأ";

    return;
  }

  dialogList =
    data.dialogs;

  renderDialogs(
    dialogList
  );
}

function renderDialogs(list) {

  dialogs.innerHTML =
    "";

  list.forEach(
    dialog => {

      const item =
        document.createElement(
          "div"
        );

      item.className =
        "dialog";

      const firstLetter =
        dialog.name
          .charAt(0)
          .toUpperCase();

      item.innerHTML =
        `
        <div class="avatar">
          ${firstLetter}
        </div>

        <div class="dialog-info">

          <div class="dialog-name">
            ${escapeHtml(
              dialog.name
            )}
          </div>

          <div class="last-message">
            ${escapeHtml(
              dialog.lastMessage
            )}
          </div>

        </div>
        `;

      item.onclick =
        () =>
          openDialog(
            dialog
          );

      dialogs.appendChild(
        item
      );
    }
  );
}

/* SEARCH */

searchInput.oninput =
  () => {

    const value =
      searchInput.value
        .toLowerCase()
        .trim();

    const filtered =
      dialogList.filter(
        dialog =>
          dialog.name
            .toLowerCase()
            .includes(
              value
            )
      );

    renderDialogs(
      filtered
    );
  };

/* OPEN CHAT */

async function openDialog(
  dialog
) {

  currentDialog =
    dialog;

  emptyChat.classList.add(
    "hidden"
  );

  chatPage.classList.remove(
    "hidden"
  );

  chatHeader.textContent =
    dialog.name;

  messages.innerHTML =
    "جاري تحميل الرسائل...";

  const data =
    await request(
      `/api/messages/${encodeURIComponent(
        dialog.id
      )}`
    );

  if (!data.success) {

    messages.innerHTML =
      "تعذر تحميل الرسائل";

    return;
  }

  renderMessages(
    data.messages
  );
}

/* RENDER MESSAGES */

function renderMessages(list) {

  messages.innerHTML =
    "";

  list.forEach(
    message =>
      addMessage(
        message
      )
  );

  scrollBottom();
}

function addMessage(
  message
) {

  const item =
    document.createElement(
      "div"
    );

  item.className =
    "message" +
    (
      message.out
        ? " out"
        : ""
    );

  if (message.text) {

    item.textContent =
      message.text;

  } else if (
    message.photo
  ) {

    item.textContent =
      "📷 صورة";

  } else if (
    message.document
  ) {

    item.textContent =
      "📎 ملف";

  } else {

    item.textContent =
      "رسالة";
  }

  messages.appendChild(
    item
  );
}

function scrollBottom() {

  messages.scrollTop =
    messages.scrollHeight;
}

/* SEND MESSAGE */

document
  .getElementById(
    "sendBtn"
  )
  .onclick =
  sendMessage;

messageInput.onkeydown =
  event => {

    if (
      event.key ===
        "Enter" &&
      !event.shiftKey
    ) {

      event.preventDefault();

      sendMessage();
    }
  };

async function sendMessage() {

  if (!currentDialog) {
    return;
  }

  const text =
    messageInput.value.trim();

  if (!text) {
    return;
  }

  messageInput.value =
    "";

  try {

    const data =
      await request(
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
              text
            })
        }
      );

    if (!data.success) {
      throw new Error(
        data.message
      );
    }

    addMessage(
      data.message
    );

    scrollBottom();

  } catch (error) {

    alert(
      error.message
    );
  }
}

/* FILE */

fileInput.onchange =
  async () => {

    if (
      !currentDialog ||
      !fileInput.files.length
    ) {
      return;
    }

    const formData =
      new FormData();

    formData.append(
      "file",
      fileInput.files[0]
    );

    try {

      const response =
        await fetch(
          `/api/files/${encodeURIComponent(
            currentDialog.id
          )}`,
          {
            method:
              "POST",
            body:
              formData
          }
        );

      const data =
        await response.json();

      if (!data.success) {
        throw new Error(
          data.message
        );
      }

      addMessage(
        data.message
      );

      scrollBottom();

    } catch (error) {

      alert(
        error.message
      );

    } finally {

      fileInput.value =
        "";
    }
  };

/* SETTINGS */

document
  .getElementById(
    "settingsBtn"
  )
  .onclick =
  () => {

    document
      .getElementById(
        "profileInfo"
      )
      .innerHTML =
      `
      <p>
        <strong>الاسم:</strong>
        ${escapeHtml(
          currentUser.name
        )}
      </p>

      <p>
        <strong>المعرف:</strong>
        ${
          currentUser.username
            ? "@" +
              escapeHtml(
                currentUser.username
              )
            : "لا يوجد"
        }
      </p>
      `;

    settingsModal.classList.remove(
      "hidden"
    );
  };

document
  .getElementById(
    "closeSettings"
  )
  .onclick =
  () =>
    settingsModal.classList.add(
      "hidden"
    );

document
  .getElementById(
    "darkModeBtn"
  )
  .onclick =
  () => {

    document.body.classList.toggle(
      "dark"
    );
  };

document
  .getElementById(
    "logoutBtn"
  )
  .onclick =
  async () => {

    await request(
      "/api/logout",
      {
        method:
          "POST"
      }
    );

    settingsModal.classList.add(
      "hidden"
    );

    showLogin();
  };

function escapeHtml(text) {

  const div =
    document.createElement(
      "div"
    );

  div.textContent =
    text || "";

  return div.innerHTML;
}

/* CHECK LOGIN */

(async () => {

  try {

    const data =
      await request(
        "/api/me"
      );

    if (
      data.authenticated
    ) {

      currentUser =
        data.user;

      showApp();

      loadDialogs();

    } else {

      showLogin();
    }

  } catch {

    showLogin();
  }

})();
