import telebot
import requests
import json
import sqlite3
from datetime import datetime

# ========== بياناتك ==========
BOT_TOKEN = '8857994405:AAFfz4TM1EdwPAz5kXRJDfsU61g389GJ8VA'
API_KEY = '3f922dc528330f4159e300d651518d0f'
ADMIN_ID = 2002553890  # ايدي المشرف
ADMIN_USERNAME = '@M12ip12'  # يوزر المشرف للتواصل
BOT_NAME = 'رقمي | Raqmi'
PRICE_MULTIPLIER = 1.5  # زيادة 50% (مخفية عن المستخدم)
BASE_URL = 'https://grizzlysms.com/stubs/handler_api.php'

# ========== تهيئة البوت وقاعدة البيانات ==========
bot = telebot.TeleBot(BOT_TOKEN)
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance REAL DEFAULT 0,
        first_name TEXT,
        username TEXT,
        reg_date TEXT
    )
''')
conn.commit()

# ========== دوال API الخاصة بـ Grizzly SMS ==========
def api_request(action, **params):
    params['api_key'] = API_KEY
    params['action'] = action
    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        return resp.text
    except Exception as e:
        return f'ERROR:{str(e)}'

def get_countries():
    """جلب قائمة الدول مع الأسعار (إن وجدت)"""
    resp = api_request('getCountries')
    try:
        data = json.loads(resp)
        if isinstance(data, dict):
            countries = []
            for code, name in data.items():
                # جلب السعر لكل دولة (اختياري)
                price = get_price(code, 'tg')  # نأخذ سعر تلغرام كمرجع
                countries.append({'code': code, 'name': name, 'price': price})
            return countries
        return []
    except:
        return []

def get_price(country, service):
    """الحصول على السعر الأصلي من الموقع"""
    resp = api_request('getPrice', country=country, service=service)
    try:
        data = json.loads(resp)
        return float(data.get('price', 0.5))
    except:
        return 0.5

def buy_number(country, service):
    """شراء رقم"""
    resp = api_request('getNumber', country=country, service=service)
    if resp.startswith('ACCESS_NUMBER'):
        parts = resp.split(':')
        if len(parts) >= 3:
            return {'id': parts[1], 'phone': parts[2]}
    return None

def get_sms_code(order_id):
    """الحصول على رمز التفعيل"""
    resp = api_request('getStatus', id=order_id)
    if resp.startswith('STATUS_WAIT_CODE'):
        parts = resp.split(':')
        if len(parts) >= 2:
            return parts[1]
    return None

def cancel_order(order_id):
    """إلغاء الطلب"""
    resp = api_request('cancelNumber', id=order_id)
    return resp == 'ACCESS_CANCEL'

# ========== دوال المستخدمين ==========
def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0.0

def update_balance(user_id, new_bal):
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, user_id))
    conn.commit()

def add_user(user_id, first_name, username):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, username, reg_date) VALUES (?,?,?,?)",
                   (user_id, first_name, username, datetime.now().isoformat()))
    conn.commit()

# ========== أوامر البوت ==========
@bot.message_handler(commands=['start'])
def start_cmd(msg):
    user = msg.from_user
    add_user(user.id, user.first_name or '', user.username or '')
    welcome_text = f"""
👋 أهلاً بك في بوت {BOT_NAME}!

📌 يمكنك شراء أرقام وهمية لتلغرام وواتساب بسهولة.

🔹 لعرض رصيدك: /balance
🔹 لشراء رقم: /buy
🔹 معرفك (User ID): `{user.id}`

📞 للشحن أو الدعم: {ADMIN_USERNAME}
"""
    # إضافة أزرار رئيسية
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("🛒 شراء رقم", callback_data="main_buy"),
        telebot.types.InlineKeyboardButton("💰 رصيدي", callback_data="main_balance")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("📞 شحن حسابي", callback_data="main_charge"),
        telebot.types.InlineKeyboardButton("🆔 معرفي", callback_data="main_id")
    )
    bot.reply_to(msg, welcome_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['balance'])
def balance_cmd(msg):
    bal = get_balance(msg.from_user.id)
    bot.reply_to(msg, f"💰 رصيدك الحالي: {bal:.2f} دولار")

@bot.message_handler(commands=['buy'])
def buy_cmd(msg):
    uid = msg.from_user.id
    if get_balance(uid) <= 0:
        bot.reply_to(msg, f"⚠️ رصيدك غير كافٍ. يرجى الشحن عبر {ADMIN_USERNAME}")
        return
    # عرض اختيار الخدمة
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📱 تلغرام", callback_data="service_tg"),
        telebot.types.InlineKeyboardButton("💬 واتساب", callback_data="service_wa")
    )
    bot.reply_to(msg, "اختر الخدمة التي تريد رقمًا لها:", reply_markup=markup)

# ========== معالجة الأزرار ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('main_'))
def main_buttons(call):
    if call.data == 'main_buy':
        # تنفيذ أمر الشراء
        buy_cmd(call.message)
        bot.answer_callback_query(call.id)
    elif call.data == 'main_balance':
        balance_cmd(call.message)
        bot.answer_callback_query(call.id)
    elif call.data == 'main_charge':
        bot.send_message(call.message.chat.id, f"📞 للشحن، تواصل مع المشرف: {ADMIN_USERNAME}")
        bot.answer_callback_query(call.id)
    elif call.data == 'main_id':
        user_id = call.from_user.id
        bot.send_message(call.message.chat.id, f"🆔 معرفك (User ID): `{user_id}`", parse_mode='Markdown')
        bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('service_'))
def service_callback(call):
    service_code = call.data.split('_')[1]  # tg أو wa
    countries = get_countries()
    if not countries:
        bot.answer_callback_query(call.id, "حدث خطأ في جلب الدول، حاول مجدداً.")
        return
    # بناء أزرار الدول مع الأسعار
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    for c in countries[:30]:  # حد أقصى 30 دولة
        price = c.get('price', 0.5) * PRICE_MULTIPLIER
        btn_text = f"{c['name']} (${price:.2f})"
        markup.add(telebot.types.InlineKeyboardButton(btn_text, callback_data=f"country_{c['code']}_{service_code}"))
    markup.add(telebot.types.InlineKeyboardButton("🔄 تحديث القائمة", callback_data=f"refresh_{service_code}"))
    bot.edit_message_text("🌍 اختر الدولة التي تريد رقمًا منها:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    bot.answer_callback_query(call.id)

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
        bot.answer_callback_query(call.id, f"⚠️ رصيدك غير كافٍ. تحتاج {final_price:.2f} دولار.")
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

    # إشعار للمشرف
    bot.send_message(ADMIN_ID, f"🛒 عملية شراء جديدة:\nالمستخدم: {call.from_user.first_name} (ID: {uid})\nالخدمة: {service_code}\nالدولة: {country_code}\nالرقم: {result['phone']}\nالسعر: {final_price:.2f}")

    # أزرار للحصول على الرمز أو الإلغاء
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('refresh_'))
def refresh_countries(call):
    service_code = call.data.split('_')[1]
    countries = get_countries()
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    for c in countries[:30]:
        price = c.get('price', 0.5) * PRICE_MULTIPLIER
        btn_text = f"{c['name']} (${price:.2f})"
        markup.add(telebot.types.InlineKeyboardButton(btn_text, callback_data=f"country_{c['code']}_{service_code}"))
    markup.add(telebot.types.InlineKeyboardButton("🔄 تحديث القائمة", callback_data=f"refresh_{service_code}"))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    bot.answer_callback_query(call.id, "تم تحديث القائمة")

# ========== أوامر المشرف ==========
@bot.message_handler(commands=['addbalance'])
def add_balance_cmd(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "⛔ هذا الأمر للمشرف فقط.")
        return
    try:
        parts = msg.text.split()
        if len(parts) < 3:
            bot.reply_to(msg, "❌ الاستخدام: /addbalance <user_id> <المبلغ>")
            return
        target_id = int(parts[1])
        amount = float(parts[2])
        if amount <= 0:
            bot.reply_to(msg, "❌ المبلغ يجب أن يكون موجباً.")
            return
        current = get_balance(target_id)
        new = current + amount
        update_balance(target_id, new)
        bot.reply_to(msg, f"✅ تم إضافة {amount} دولار للمستخدم {target_id}. الرصيد الجديد: {new:.2f}")
        bot.send_message(target_id, f"💰 تم شحن رصيدك بمبلغ {amount} دولار. رصيدك الحالي: {new:.2f}")
    except Exception as e:
        bot.reply_to(msg, f"❌ خطأ: {str(e)}")

@bot.message_handler(commands=['setprice'])
def set_price_cmd(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        parts = msg.text.split()
        if len(parts) < 2:
            bot.reply_to(msg, "الاستخدام: /setprice <النسبة المئوية> مثلاً 50 يعني زيادة 50%")
            return
        percent = float(parts[1])
        global PRICE_MULTIPLIER
        PRICE_MULTIPLIER = 1 + percent / 100
        bot.reply_to(msg, f"✅ تم تعديل نسبة الزيادة إلى {percent}% (السعر النهائي = سعر الموقع × {PRICE_MULTIPLIER:.2f})")
    except:
        bot.reply_to(msg, "❌ أدخل رقماً صحيحاً.")

# ========== تشغيل البوت ==========
print("🤖 البوت يعمل...")
bot.infinity_polling()
