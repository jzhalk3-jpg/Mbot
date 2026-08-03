import telebot
import requests
import json
import sqlite3
import random
from datetime import datetime

# ========== بياناتك ==========
BOT_TOKEN = '8857994405:AAFfz4TM1EdwPAz5kXRJDfsU61g389GJ8VA'
API_KEY = '3f922dc528330f4159e300d651518d0f'
ADMIN_ID = 2002553890
ADMIN_USERNAME = '@M12ip12'
BOT_NAME = 'رقمي | Raqmi'
PRICE_MULTIPLIER = 1.5
BASE_URL = 'https://grizzlysms.com/stubs/handler_api.php'

# ========== قاموس ترجمة الدول (الاسم العربي + العلم) ==========
COUNTRIES_MAP = {
    'sa': {'name': '🇸🇦 السعودية'},
    'ae': {'name': '🇦🇪 الإمارات'},
    'us': {'name': '🇺🇸 الولايات المتحدة'},
    'uk': {'name': '🇬🇧 بريطانيا'},
    'eg': {'name': '🇪🇬 مصر'},
    'kw': {'name': '🇰🇼 الكويت'},
    'qa': {'name': '🇶🇦 قطر'},
    'tr': {'name': '🇹🇷 تركيا'},
    'de': {'name': '🇩🇪 ألمانيا'},
    'fr': {'name': '🇫🇷 فرنسا'},
    'it': {'name': '🇮🇹 إيطاليا'},
    'es': {'name': '🇪🇸 إسبانيا'},
    'ru': {'name': '🇷🇺 روسيا'},
    'in': {'name': '🇮🇳 الهند'},
    'cn': {'name': '🇨🇳 الصين'},
    'jp': {'name': '🇯🇵 اليابان'},
    'kr': {'name': '🇰🇷 كوريا'},
    'br': {'name': '🇧🇷 البرازيل'},
    'mx': {'name': '🇲🇽 المكسيك'},
    'ca': {'name': '🇨🇦 كندا'},
    'au': {'name': '🇦🇺 أستراليا'},
    'id': {'name': '🇮🇩 إندونيسيا'},
    'pk': {'name': '🇵🇰 باكستان'},
    'bd': {'name': '🇧🇩 بنغلاديش'},
    'ng': {'name': '🇳🇬 نيجيريا'},
    'za': {'name': '🇿🇦 جنوب أفريقيا'},
    'ar': {'name': '🇦🇷 الأرجنتين'},
    'ch': {'name': '🇨🇭 سويسرا'},
    'nl': {'name': '🇳🇱 هولندا'},
    'se': {'name': '🇸🇪 السويد'},
    'no': {'name': '🇳🇴 النرويج'},
    'dk': {'name': '🇩🇰 الدنمارك'},
    'fi': {'name': '🇫🇮 فنلندا'},
    'pl': {'name': '🇵🇱 بولندا'},
    'ua': {'name': '🇺🇦 أوكرانيا'},
    'ir': {'name': '🇮🇷 إيران'},
    'iq': {'name': '🇮🇶 العراق'},
    'sy': {'name': '🇸🇾 سوريا'},
    'jo': {'name': '🇯🇴 الأردن'},
    'lb': {'name': '🇱🇧 لبنان'},
    'ps': {'name': '🇵🇸 فلسطين'},
    'ye': {'name': '🇾🇪 اليمن'},
    'bh': {'name': '🇧🇭 البحرين'},
    'om': {'name': '🇴🇲 عمان'},
}

# ========== تهيئة البوت وقاعدة البيانات ==========
bot = telebot.TeleBot(BOT_TOKEN)
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        account_number INTEGER UNIQUE,
        balance REAL DEFAULT 0,
        first_name TEXT,
        username TEXT,
        reg_date TEXT
    )
''')
conn.commit()

# ========== دوال API ==========
def api_request(action, **params):
    params['api_key'] = API_KEY
    params['action'] = action
    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        return resp.text
    except:
        return 'ERROR'

def get_countries():
    resp = api_request('getCountries')
    try:
        data = json.loads(resp)
        if isinstance(data, dict):
            countries = []
            for code, name in data.items():
                price = get_price(code, 'tg')
                countries.append({'code': code, 'name': name, 'price': price})
            return countries
        return []
    except:
        return []

def get_price(country, service):
    resp = api_request('getPrice', country=country, service=service)
    try:
        data = json.loads(resp)
        return float(data.get('price', 0.5))
    except:
        return 0.5

def buy_number(country, service):
    resp = api_request('getNumber', country=country, service=service)
    if resp.startswith('ACCESS_NUMBER'):
        parts = resp.split(':')
        if len(parts) >= 3:
            return {'id': parts[1], 'phone': parts[2]}
    return None

def get_sms_code(order_id):
    resp = api_request('getStatus', id=order_id)
    if resp.startswith('STATUS_WAIT_CODE'):
        parts = resp.split(':')
        if len(parts) >= 2:
            return parts[1]
    return None

def cancel_order(order_id):
    resp = api_request('cancelNumber', id=order_id)
    return resp == 'ACCESS_CANCEL'

# ========== دوال المستخدمين ==========
def generate_account_number():
    while True:
        num = random.randint(10000, 99999)
        cursor.execute("SELECT user_id FROM users WHERE account_number=?", (num,))
        if not cursor.fetchone():
            return num

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0.0

def update_balance(user_id, new_bal):
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, user_id))
    conn.commit()

def add_user(user_id, first_name, username):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, account_number, first_name, username, reg_date) VALUES (?,?,?,?,?)",
                   (user_id, generate_account_number(), first_name, username, datetime.now().isoformat()))
    conn.commit()

def get_account_number(user_id):
    cursor.execute("SELECT account_number FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None

# ========== أوامر البوت ==========
@bot.message_handler(commands=['start'])
def start_cmd(msg):
    user = msg.from_user
    add_user(user.id, user.first_name or '', user.username or '')
    bal = get_balance(user.id)
    acc_num = get_account_number(user.id)
    
    welcome_text = f"""
👋 أهلاً بك في بوت {BOT_NAME}!

📌 حسابك: `{acc_num}`
💰 رصيدك الحالي: {bal:.2f} دولار
🆔 معرفك (User ID): `{user.id}`

📞 للشحن أو الدعم: {ADMIN_USERNAME}

استخدم الزر أدناه لبدء الشراء.
"""
    markup = telebot.types.InlineKeyboardMarkup()
    # زر شراء رقم
    markup.add(telebot.types.InlineKeyboardButton("🛒 شراء رقم", callback_data="main_buy"))
    # زر شحن حسابي (للمستخدمين)
    markup.add(telebot.types.InlineKeyboardButton("📞 شحن حسابي", callback_data="main_charge"))
    # زر نسخ رقم الحساب
    markup.add(telebot.types.InlineKeyboardButton("📋 نسخ رقم الحساب", callback_data=f"copy_acc_{acc_num}"))
    
    bot.reply_to(msg, welcome_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['balance'])
def balance_cmd(msg):
    bal = get_balance(msg.from_user.id)
    bot.reply_to(msg, f"💰 رصيدك الحالي: {bal:.2f} دولار")

@bot.message_handler(commands=['buy'])
def buy_cmd(msg):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📱 تلغرام", callback_data="service_tg"),
        telebot.types.InlineKeyboardButton("💬 واتساب", callback_data="service_wa")
    )
    bot.reply_to(msg, "اختر الخدمة التي تريد رقمًا لها:", reply_markup=markup)

# ========== أوامر المشرف (لوحة التحكم) ==========
@bot.message_handler(commands=['admin'])
def admin_panel(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("➕ شحن مستخدم", callback_data="admin_charge"))
    markup.add(telebot.types.InlineKeyboardButton("🔧 تعديل نسبة الربح", callback_data="admin_price"))
    bot.reply_to(msg, "👨‍💻 لوحة تحكم المشرف:", reply_markup=markup)

# متغيرات مؤقتة لخطوات الشحن
temp_data = {}

@bot.callback_query_handler(func=lambda call: call.data == 'admin_charge')
def admin_charge_step1(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "غير مصرح")
        return
    msg = bot.send_message(call.message.chat.id, "📝 أرسل **معرف المستخدم (User ID)** الذي تريد شحنه:")
    bot.register_next_step_handler(msg, admin_charge_step2)
    bot.answer_callback_query(call.id)

def admin_charge_step2(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        uid = int(msg.text)
        temp_data['charge_uid'] = uid
        msg2 = bot.reply_to(msg, "💰 أرسل **المبلغ** الذي تريد إضافته (بالدولار):")
        bot.register_next_step_handler(msg2, admin_charge_step3)
    except:
        bot.reply_to(msg, "❌ خطأ: المعرف يجب أن يكون أرقاماً فقط. حاول مجدداً باستخدام /admin")

def admin_charge_step3(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        amount = float(msg.text)
        if amount <= 0:
            bot.reply_to(msg, "❌ المبلغ يجب أن يكون موجباً.")
            return
        uid = temp_data.get('charge_uid')
        if not uid:
            bot.reply_to(msg, "❌ حدث خطأ، استخدم /admin مجدداً.")
            return
        current = get_balance(uid)
        new = current + amount
        update_balance(uid, new)
        bot.reply_to(msg, f"✅ تم إضافة {amount} دولار للمستخدم {uid}. الرصيد الجديد: {new:.2f}")
        bot.send_message(uid, f"💰 تم شحن رصيدك بمبلغ {amount} دولار. رصيدك الحالي: {new:.2f}")
        temp_data['charge_uid'] = None
    except:
        bot.reply_to(msg, "❌ خطأ: المبلغ يجب أن يكون رقماً. حاول مجدداً باستخدام /admin")

@bot.callback_query_handler(func=lambda call: call.data == 'admin_price')
def admin_price_step1(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "غير مصرح")
        return
    msg = bot.send_message(call.message.chat.id, "📝 أرسل **نسبة الزيادة** المئوية (مثال: 50 يعني زيادة 50%):")
    bot.register_next_step_handler(msg, admin_price_step2)
    bot.answer_callback_query(call.id)

def admin_price_step2(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        percent = float(msg.text)
        global PRICE_MULTIPLIER
        PRICE_MULTIPLIER = 1 + percent / 100
        bot.reply_to(msg, f"✅ تم تعديل نسبة الزيادة إلى {percent}% (السعر النهائي = سعر الموقع × {PRICE_MULTIPLIER:.2f})")
    except:
        bot.reply_to(msg, "❌ خطأ: أدخل رقماً صحيحاً. حاول مجدداً باستخدام /admin")

# ========== معالجة الأزرار الرئيسية ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('main_'))
def main_buttons(call):
    if call.data == 'main_buy':
        buy_cmd(call.message)
        bot.answer_callback_query(call.id)
    elif call.data == 'main_charge':
        bot.send_message(call.message.chat.id, f"📞 للشحن، تواصل مع المشرف: {ADMIN_USERNAME}")
        bot.answer_callback_query(call.id)
    elif call.data.startswith('copy_acc_'):
        acc_num = call.data.split('_')[2]
        bot.send_message(call.message.chat.id, f"📋 تم نسخ رقم حسابك: `{acc_num}`", parse_mode='Markdown')
        bot.answer_callback_query(call.id)

# ========== معالجة الخدمات والدول مع الترجمة والتقليب ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('service_'))
def service_callback(call):
    service_code = call.data.split('_')[1]
    # عرض الصفحة الأولى
    show_countries_page(call.message.chat.id, call.message.message_id, service_code, page=0)

def show_countries_page(chat_id, msg_id, service_code, page):
    countries = get_countries()
    if not countries:
        bot.send_message(chat_id, "حدث خطأ في جلب الدول، حاول مجدداً.")
        return
    
    # ترجمة الأسماء وإضافة الأعلام
    translated = []
    for c in countries:
        code = c['code']
        if code in COUNTRIES_MAP:
            name = COUNTRIES_MAP[code]['name']
        else:
            name = f"🌍 {code.upper()}"  # احتياطي للدول غير المدرجة
        price = c.get('price', 0.5) * PRICE_MULTIPLIER
        translated.append({'code': code, 'display': name, 'price': price})
    
    # ترتيب حسب الاسم العربي
    translated.sort(key=lambda x: x['display'])
    
    # تحديد الصفحة
    items_per_page = 10
    total_pages = (len(translated) + items_per_page - 1) // items_per_page
    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0
    
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(translated))
    page_items = translated[start_idx:end_idx]
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    for item in page_items:
        btn_text = f"{item['display']} (${item['price']:.2f})"
        callback_data = f"country_{item['code']}_{service_code}"
        markup.add(telebot.types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    
    # أزرار التقليب
    nav_buttons = []
    if page > 0:
        nav_buttons.append(telebot.types.InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{service_code}_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(telebot.types.InlineKeyboardButton("التالي ➡️", callback_data=f"page_{service_code}_{page+1}"))
    if nav_buttons:
        markup.add(*nav_buttons)
    
    # زر تحديث
    markup.add(telebot.types.InlineKeyboardButton("🔄 تحديث القائمة", callback_data=f"refresh_{service_code}"))
    
    # تعديل الرسالة أو إرسالها
    try:
        bot.edit_message_text(f"🌍 اختر الدولة (الصفحة {page+1}/{total_pages}):", chat_id=chat_id, message_id=msg_id, reply_markup=markup)
    except:
        bot.send_message(chat_id, f"🌍 اختر الدولة (الصفحة {page+1}/{total_pages}):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def page_callback(call):
    parts = call.data.split('_')
    service_code = parts[1]
    page = int(parts[2])
    show_countries_page(call.message.chat.id, call.message.message_id, service_code, page)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('refresh_'))
def refresh_countries(call):
    service_code = call.data.split('_')[1]
    show_countries_page(call.message.chat.id, call.message.message_id, service_code, page=0)
    bot.answer_callback_query(call.id, "تم التحديث")

# ========== معالجة اختيار الدولة ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('country_'))
def country_callback(call):
    parts = call.data.split('_')
    country_code = parts[1]
    service_code = parts[2]
    uid = call.from_user.id

    original_price = get_price(country_code, service_code)
    final_price = original_price * PRICE_MULTIPLIER
    bal = get_balance(uid)

    if bal < final_price:
        bot.answer_callback_query(call.id, f"⚠️ رصيدك غير كافٍ. تحتاج {final_price:.2f} دولار. قم بالشحن عبر {ADMIN_USERNAME}")
        return

    result = buy_number(country_code, service_code)
    if not result:
        bot.answer_callback_query(call.id, "❌ فشل شراء الرقم، حاول مجدداً.")
        return

    new_bal = bal - final_price
    update_balance(uid, new_bal)

    response_text = f"""
✅ تم شراء الرقم بنجاح!

📞 الرقم: `{result['phone']}`
🆔 رقم الطلب: {result['id']}
💰 السعر المدفوع: {final_price:.2f} دولار
💵 رصيدك المتبقي: {new_bal:.2f} دولار

⏳ سيتم إرسال رمز التفعيل إلى الرقم خلال دقائق.
    """
    bot.send_message(call.message.chat.id, response_text, parse_mode='Markdown')

    bot.send_message(ADMIN_ID, f"🛒 عملية شراء جديدة:\nالمستخدم: {call.from_user.first_name} (ID: {uid})\nالخدمة: {service_code}\nالدولة: {country_code}\nالرقم: {result['phone']}\nالسعر: {final_price:.2f}")

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📩 الحصول على رمز التفعيل", callback_data=f"getcode_{result['id']}"),
        telebot.types.InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"cancel_{result['id']}")
    )
    bot.send_message(call.message.chat.id, "اختر إجراء:", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('getcode_'))
def get_code_callback(call):
    order_id = call.data.split('_')[1]
    code = get_sms_code(order_id)
    if code:
        bot.send_message(call.message.chat.id, f"🔑 رمز التفعيل: `{code}`", parse_mode='Markdown')
    else:
        bot.send_message(call.message.chat.id, "⏳ لم يصل الرمز بعد، انتظر قليلاً ثم حاول مجدداً.")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def cancel_callback(call):
    order_id = call.data.split('_')[1]
    if cancel_order(order_id):
        bot.send_message(call.message.chat.id, "✅ تم إلغاء الطلب واسترداد الرصيد (إن كان مدفوعاً).")
    else:
        bot.send_message(call.message.chat.id, "❌ فشل الإلغاء.")
    bot.answer_callback_query(call.id)

# ========== تشغيل البوت ==========
print("🤖 البوت يعمل...")
bot.infinity_polling()
