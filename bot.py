import telebot
import requests
import json
import sqlite3
import time
from datetime import datetime

# ========================
# البيانات
# ========================
BOT_TOKEN = '8857994405:AAFfz4TM1EdwPAz5kXRJDfsU61g389GJ8VA'
API_KEY = '3f922dc528330f4159e300d651518d0f'
ADMIN_ID = 2002553890
ADMIN_USERNAME = '@M12ip12'  # يوزر المشرف للتواصل
BOT_NAME = 'رقمي | Raqmi'

# نسبة الزيادة (مخفية عن المستخدمين)
PRICE_MULTIPLIER = 1.5

BASE_URL = 'https://grizzlysms.com/stubs/handler_api.php'

# ========================
# تهيئة البوت وقاعدة البيانات
# ========================
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

# ========================
# دوال API
# ========================
def api_request(action, **params):
    params['api_key'] = API_KEY
    params['action'] = action
    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        return resp.text
    except Exception as e:
        return f'ERROR:{str(e)}'

def get_countries():
    response = api_request('getCountries')
    try:
        data = json.loads(response)
        if isinstance(data, dict):
            return [{'code': code, 'name': name} for code, name in data.items()]
        elif isinstance(data, list):
            return [{'code': c, 'name': c} for c in data]
        else:
            return []
    except:
        return []

def buy_number(country_code, service_code):
    response = api_request('getNumber', country=country_code, service=service_code)
    if response.startswith('ACCESS_NUMBER'):
        parts = response.split(':')
        if len(parts) >= 3:
            return {'id': parts[1], 'phone': parts[2]}
    return None

def get_sms_code(order_id):
    response = api_request('getStatus', id=order_id)
    if response.startswith('STATUS_WAIT_CODE'):
        parts = response.split(':')
        if len(parts) >= 2:
            return parts[1]
    return None

def cancel_order(order_id):
    response = api_request('cancelNumber', id=order_id)
    return response == 'ACCESS_CANCEL'

def get_price(country_code, service_code):
    response = api_request('getPrice', country=country_code, service=service_code)
    try:
        data = json.loads(response)
        if 'price' in data:
            return float(data['price'])
        else:
            return 0.5
    except:
        return 0.5

# ========================
# دوال المستخدمين
# ========================
def get_user_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def update_user_balance(user_id, new_balance):
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_balance, user_id))
    conn.commit()

def add_user(user_id, first_name, username):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, username, reg_date) VALUES (?, ?, ?, ?)",
                   (user_id, first_name, username, datetime.now().isoformat()))
    conn.commit()

# ========================
# أوامر البوت
# ========================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    add_user(user_id, message.from_user.first_name or '', message.from_user.username or '')
    welcome_text = f"""
👋 أهلاً بك في بوت {BOT_NAME}!

يمكنك شراء أرقام وهمية لتلغرام وواتساب بسهولة.
استخدم الأوامر التالية:

/buy - لشراء رقم
/balance - لعرض رصيدك
/help - للمساعدة

🔹 للشحن، تواصل مع المشرف {ADMIN_USERNAME}
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    help_text = f"""
📌 الأوامر المتاحة:
/buy - شراء رقم وهمي
/balance - معرفة رصيدك
/start - إعادة الترحيب

📞 للشحن أو الدعم، تواصل مع {ADMIN_USERNAME}
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['balance'])
def balance_cmd(message):
    bal = get_user_balance(message.from_user.id)
    bot.reply_to(message, f"💰 رصيدك الحالي: {bal:.2f} دولار")

@bot.message_handler(commands=['buy'])
def buy_start(message):
    user_id = message.from_user.id
    if get_user_balance(user_id) <= 0:
        bot.reply_to(message, f"⚠️ رصيدك غير كافٍ. يرجى شحن رصيدك عبر التواصل مع {ADMIN_USERNAME}.")
        return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📱 تلغرام", callback_data="service_tg"),
        telebot.types.InlineKeyboardButton("💬 واتساب", callback_data="service_wa")
    )
    bot.reply_to(message, "اختر الخدمة التي تريد رقمًا لها:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('service_'))
def service_callback(call):
    service_code = call.data.split('_')[1]
    countries = get_countries()
    if not countries:
        bot.answer_callback_query(call.id, "حدث خطأ في جلب الدول، حاول مجدداً.")
        return
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    for c in countries[:30]:
        markup.add(telebot.types.InlineKeyboardButton(c['name'], callback_data=f"country_{c['code']}_{service_code}"))
    markup.add(telebot.types.InlineKeyboardButton("🔄 تحديث القائمة", callback_data="refresh_countries"))
    bot.edit_message_text("🌍 اختر الدولة:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('country_'))
def country_callback(call):
    parts = call.data.split('_')
    country_code = parts[1]
    service_code = parts[2]
    
    original_price = get_price(country_code, service_code)
    if original_price <= 0:
        original_price = 0.5
    final_price = original_price * PRICE_MULTIPLIER
    
    user_id = call.from_user.id
    bal = get_user_balance(user_id)
    if bal < final_price:
        bot.answer_callback_query(call.id, f"⚠️ رصيدك غير كافٍ. تحتاج {final_price:.2f} دولار.")
        return
    
    result = buy_number(country_code, service_code)
    if not result:
        bot.answer_callback_query(call.id, "❌ فشل شراء الرقم، حاول مجدداً.")
        return
    
    order_id = result['id']
    phone = result['phone']
    new_bal = bal - final_price
    update_user_balance(user_id, new_bal)
    
    response_text = f"""
✅ تم شراء الرقم بنجاح!

📞 الرقم: `{phone}`
🆔 رقم الطلب: {order_id}
💰 السعر المدفوع: {final_price:.2f} دولار
💵 رصيدك المتبقي: {new_bal:.2f} دولار

⏳ سيتم إرسال رمز التفعيل إلى الرقم خلال دقائق.
    """
    bot.send_message(call.message.chat.id, response_text, parse_mode='Markdown')
    
    # إشعار للمشرف
    bot.send_message(ADMIN_ID, f"🛒 عملية شراء جديدة:\nالمستخدم: {call.from_user.first_name} (ID: {user_id})\nالخدمة: {service_code}\nالدولة: {country_code}\nالرقم: {phone}\nالسعر المدفوع: {final_price}")
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📩 الحصول على رمز التفعيل", callback_data=f"getcode_{order_id}"),
        telebot.types.InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"cancel_{order_id}")
    )
    bot.send_message(call.message.chat.id, "هل تريد الحصول على رمز التفعيل الآن؟", reply_markup=markup)
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

@bot.callback_query_handler(func=lambda call: call.data == 'refresh_countries')
def refresh_countries(call):
    countries = get_countries()
    # استنتاج service_code من الزر الأول
    service_code = call.message.reply_markup.inline_keyboard[0][0].callback_data.split('_')[1]
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    for c in countries[:30]:
        markup.add(telebot.types.InlineKeyboardButton(c['name'], callback_data=f"country_{c['code']}_{service_code}"))
    markup.add(telebot.types.InlineKeyboardButton("🔄 تحديث القائمة", callback_data="refresh_countries"))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    bot.answer_callback_query(call.id, "تم التحديث")

# ========================
# أوامر المشرف
# ========================
@bot.message_handler(commands=['addbalance'])
def add_balance_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ هذا الأمر للمشرف فقط.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "❌ الاستخدام: /addbalance <user_id> <المبلغ>")
            return
        target_id = int(parts[1])
        amount = float(parts[2])
        if amount <= 0:
            bot.reply_to(message, "❌ المبلغ يجب أن يكون موجباً.")
            return
        current = get_user_balance(target_id)
        new = current + amount
        update_user_balance(target_id, new)
        bot.reply_to(message, f"✅ تم إضافة {amount} دولار للمستخدم {target_id}. الرصيد الجديد: {new:.2f}")
        bot.send_message(target_id, f"💰 تم شحن رصيدك بمبلغ {amount} دولار. رصيدك الحالي: {new:.2f}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {str(e)}")

@bot.message_handler(commands=['setprice'])
def set_price_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "الاستخدام: /setprice <النسبة المئوية> مثلاً 50 يعني 1.5x")
            return
        percent = float(parts[1])
        global PRICE_MULTIPLIER
        PRICE_MULTIPLIER = 1 + percent/100
        bot.reply_to(message, f"✅ تم تعديل نسبة الزيادة إلى {percent}% (السعر النهائي = سعر الموقع × {PRICE_MULTIPLIER:.2f})")
    except:
        bot.reply_to(message, "❌ أدخل رقماً صحيحاً.")

# ========================
# تشغيل البوت
# ========================
print("🤖 البوت يعمل...")
bot.infinity_polling()
