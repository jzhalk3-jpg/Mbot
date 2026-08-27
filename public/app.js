// المتغيرات العامة
let currentChatId = null;
let currentAccountId = null;

// عناصر DOM
const loginScreen = document.getElementById('login-screen');
const mainScreen = document.getElementById('main-screen');
const phoneInput = document.getElementById('phone-input');
const sendCodeBtn = document.getElementById('send-code-btn');
const codeSection = document.getElementById('code-section');
const codeInput = document.getElementById('code-input');
const verifyCodeBtn = document.getElementById('verify-code-btn');
const passwordSection = document.getElementById('password-section');
const passwordInput = document.getElementById('password-input');
const verifyPasswordBtn = document.getElementById('verify-password-btn');
const loginError = document.getElementById('login-error');
const dialogsList = document.getElementById('dialogs-list');
const messagesContainer = document.getElementById('messages-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const fileInput = document.getElementById('file-input');
const fileBtn = document.getElementById('file-btn');
const chatHeader = document.getElementById('chat-header');
const accountSelect = document.getElementById('account-select');
const switchAccountBtn = document.getElementById('switch-account-btn');
const logoutBtn = document.getElementById('logout-btn');
const searchInput = document.getElementById('search-input');

// دوال مساعدة
function showError(msg) {
    loginError.textContent = msg;
}

function clearError() {
    loginError.textContent = '';
}

// تسجيل الدخول
sendCodeBtn.onclick = async () => {
    const phone = phoneInput.value.trim();
    if (!phone) return showError('أدخل رقم الهاتف');
    clearError();
    try {
        const res = await fetch('/api/auth/send-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        codeSection.style.display = 'block';
        sendCodeBtn.disabled = true;
    } catch (e) {
        showError(e.message);
    }
};

verifyCodeBtn.onclick = async () => {
    const code = codeInput.value.trim();
    if (!code) return showError('أدخل الرمز');
    clearError();
    try {
        const res = await fetch('/api/auth/verify-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        const data = await res.json();
        if (!data.success) {
            if (data.passwordRequired) {
                passwordSection.style.display = 'block';
                return;
            }
            throw new Error(data.message);
        }
        // تم الدخول
        await loadMain();
    } catch (e) {
        showError(e.message);
    }
};

verifyPasswordBtn.onclick = async () => {
    const password = passwordInput.value.trim();
    if (!password) return showError('أدخل كلمة المرور');
    clearError();
    try {
        const res = await fetch('/api/auth/verify-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        await loadMain();
    } catch (e) {
        showError(e.message);
    }
};

// تحميل الشاشة الرئيسية
async function loadMain() {
    loginScreen.classList.remove('active');
    mainScreen.classList.add('active');
    await loadAccounts();
    await loadDialogs();
    // بدء التحديث التلقائي كل 10 ثوانٍ
    setInterval(() => {
        if (currentChatId) loadMessages(currentChatId);
        loadDialogs();
    }, 10000);
}

// جلب الحسابات
async function loadAccounts() {
    const res = await fetch('/api/accounts');
    const data = await res.json();
    if (!data.success) return;
    const select = accountSelect;
    select.innerHTML = '';
    data.accounts.forEach(acc => {
        const opt = document.createElement('option');
        opt.value = acc.id;
        opt.textContent = `${acc.name} (${acc.phone})`;
        if (acc.active) opt.selected = true;
        select.appendChild(opt);
    });
}

// تبديل الحساب
switchAccountBtn.onclick = async () => {
    const accountId = accountSelect.value;
    if (!accountId) return;
    try {
        const res = await fetch('/api/accounts/switch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ accountId })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        currentChatId = null;
        await loadDialogs();
        messagesContainer.innerHTML = '';
        chatHeader.textContent = '';
    } catch (e) {
        alert(e.message);
    }
};

// جلب المحادثات
async function loadDialogs() {
    const res = await fetch('/api/dialogs?limit=50');
    const data = await res.json();
    if (!data.success) return;
    dialogsList.innerHTML = '';
    data.dialogs.forEach(d => {
        const div = document.createElement('div');
        div.className = 'dialog-item';
        div.innerHTML = `
            <div class="avatar">${d.name.charAt(0)}</div>
            <div class="info">
                <div class="name">${d.name}</div>
                <div class="last-msg">${d.lastMessage || ''}</div>
            </div>
        `;
        div.onclick = () => {
            currentChatId = d.id;
            loadMessages(d.id);
            chatHeader.textContent = d.name;
        };
        dialogsList.appendChild(div);
    });
}

// جلب الرسائل
async function loadMessages(chatId) {
    const res = await fetch(`/api/messages/${chatId}?limit=50`);
    const data = await res.json();
    if (!data.success) return;
    messagesContainer.innerHTML = '';
    data.messages.forEach(msg => {
        const div = document.createElement('div');
        div.className = `message ${msg.out ? 'out' : 'in'}`;
        div.innerHTML = `
            <div>${msg.text}</div>
            <div class="time">${new Date(msg.date).toLocaleTimeString()}</div>
        `;
        messagesContainer.appendChild(div);
    });
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// إرسال رسالة
sendBtn.onclick = async () => {
    if (!currentChatId) return;
    const text = messageInput.value.trim();
    if (!text) return;
    try {
        const res = await fetch(`/api/messages/${currentChatId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        const data = await res.json();
        if (data.success) {
            messageInput.value = '';
            loadMessages(currentChatId);
        }
    } catch (e) {
        alert(e.message);
    }
};

// إرسال ملف
fileBtn.onclick = () => fileInput.click();
fileInput.onchange = async () => {
    if (!currentChatId || !fileInput.files.length) return;
    const form = new FormData();
    form.append('file', fileInput.files[0]);
    try {
        const res = await fetch(`/api/files/${currentChatId}`, {
            method: 'POST',
            body: form
        });
        const data = await res.json();
        if (data.success) {
            fileInput.value = '';
            loadMessages(currentChatId);
        }
    } catch (e) {
        alert(e.message);
    }
};

// تسجيل الخروج
logoutBtn.onclick = async () => {
    if (!confirm('هل تريد تسجيل الخروج؟')) return;
    await fetch('/api/logout', { method: 'POST' });
    location.reload();
};

// البحث (تلقائي)
searchInput.oninput = async () => {
    const q = searchInput.value.trim();
    if (!q) return loadDialogs();
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!data.success) return;
    dialogsList.innerHTML = '';
    data.results.forEach(r => {
        const div = document.createElement('div');
        div.className = 'dialog-item';
        div.innerHTML = `
            <div class="avatar">${r.name.charAt(0)}</div>
            <div class="info"><div class="name">${r.name}</div></div>
        `;
        div.onclick = () => {
            currentChatId = r.id;
            loadMessages(r.id);
            chatHeader.textContent = r.name;
        };
        dialogsList.appendChild(div);
    });
};

// التحقق من الجلسة عند التحميل
(async function checkAuth() {
    try {
        const res = await fetch('/api/me');
        const data = await res.json();
        if (data.authenticated) {
            await loadMain();
        } else {
            loginScreen.classList.add('active');
        }
    } catch {
        loginScreen.classList.add('active');
    }
})();
