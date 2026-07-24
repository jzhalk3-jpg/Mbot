import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import os
import re
import threading
import logging
from datetime import datetime, timedelta
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
from pyrogram.errors import SessionPasswordNeeded, FloodWait, UserAlreadyParticipant

# 1. إعدادات السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TalaatBot")

# 2. خادم Flask لإبقاء السيرفر نشطاً
app = Flask('')

@app.route('/')
def home():
    return "Auto-Join Bot is Live and Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

t = threading.Thread(target=run_flask)
t.daemon = True
t.start()

# 3. بيانات البوت والإعدادات الخاصة بك
BOT_TOKEN = "8969957914:AAF33nKExvFFry5ImvGirDU4oYraLMX3tHc"
API_ID = 39289901
API_HASH = "a5dcef068387dd95705046f910d6cd48"

ADMIN_ID = 5064913080  
OWNER_USERNAME = "@Ra11_8h"

# قاعدة بيانات مؤقتة متكاملة لكل المستخدمين وحالة النظام العام
users_db = {}
global_users_links = []
system_status = {"is_globally_active": True}

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {
            "points": 0,
            "sessions": {},
            "links": [],
            "step": None,
            "active_session": None,
            "vip_expiry": None,  
            "referred_by": None,  
            "referral_count": 0,  
            "settings": {
                "delay_min": 5,
                "batch_limit": 5,
                "cooldown_mins": 4
            },
            "is_running": False
        }
    return users_db[user_id]

def is_vip(user_id):
    u = get_user(user_id)
    if u["vip_expiry"]:
        try:
            expiry_date = datetime.fromisoformat(u["vip_expiry"])
            if datetime.now() < expiry_date:
                return True
            else:
                u["vip_expiry"] = None 
        except:
            pass
    return False

def main_reply_keyboard(user_id):
    keyboard = [
        [KeyboardButton("📱 تسجيل الدخول الجديد"), KeyboardButton("🔗 إرسال روابط")],
        [KeyboardButton("🚀 بدء الانضمام"), KeyboardButton("🛑 إيقاف الانضمام")],
        [KeyboardButton("📱 أرقامي المسجلة"), KeyboardButton("🗑️ حذف رقم مسجل")],
        [KeyboardButton("⏱️ تحديد الوقت"), KeyboardButton("💤 استراحة الروابط")],
        [KeyboardButton("🗑️ مسح الروابط"), KeyboardButton("📊 حالة النظام")],
        [KeyboardButton("🎯 شحن نقاطك"), KeyboardButton("💎 اشتراك VIP")],
        [KeyboardButton("🎁 كسب النقاط")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("📢 إذاعة عامة"), KeyboardButton("⚡ تشغيل/إيقاف البوت العام")])
        keyboard.append([KeyboardButton("👁️‍🗨️ روابط المستخدمين (للمالك)"), KeyboardButton("🗑️ مسح أرشيف الروابط")])
        
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

bot = Client("my_ultimate_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    user_id = message.from_user.id
    u = get_user(user_id)
    
    text_args = message.text.split()
    if len(text_args) > 1 and text_args[1].startswith("ref_"):
        try:
            referrer_id = int(text_args[1].replace("ref_", ""))
            if referrer_id != user_id and u["referred_by"] is None:
                u["referred_by"] = referrer_id
                referrer_user = get_user(referrer_id)
                referrer_user["points"] += 8
                referrer_user["referral_count"] += 1
                
                try:
                    await client.send_message(
                        referrer_id, 
                        f"🎉 **مبروك!** دخل شخص جديد عبر رابط الدعوة الخاص بك.\n"
                        f"🎁 تم إضافة **8 نقاط** إلى رصيدك.\n"
                        f"👥 إجمالي الأشخاص الذين دعوتهم: `{referrer_user['referral_count']}` شخصاً\n"
                        f"🎯 رصيدك الحالي: **{referrer_user['points']}** نقطة."
                    )
                except:
                    pass
        except Exception as e:
            logger.error(f"Error handling referral: {e}")

    if not system_status["is_globally_active"] and user_id != ADMIN_ID:
        await message.reply_text("⚠️ البوت متوقف صيانة حالياً من قبل المطور. يرجى الانتظار.")
        return

    bot_info = await client.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    vip_status_text = "✨ مفعل (بدون خصم نقاط)" if is_vip(user_id) else "❌ غير مشترك"
    await message.reply_text(
        f"🎯 **مرحباً بك في لوحة تحكم اليوزر بوت!**\n"
        f"🎯 نقاطك الحالية: **{u['points']}** نقطة\n"
        f"💎 حالة اشتراك الـ VIP: **{vip_status_text}**\n\n"
        f"🎁 **ربح النقاط السريع:**\n"
        f"كل شخص يدخل البوت عبر رابط دعوتك تربح أنت **8 نقاط** فوراً!\n"
        f"🔗 رابطك الشخصي:\n`{ref_link}`\n\n"
        f"اختر ما تحتاجه من الأزرار أسفل الشاشة:",
        reply_markup=main_reply_keyboard(user_id)
    )

@bot.on_message(filters.private & filters.command("شحن"))
async def charge_user_points(client, message):
    if message.from_user.id != ADMIN_ID:
        await message.reply_text("❌ هذا الأمر خاص بمالك البوت فقط.")
        return
    
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        points_to_add = int(parts[2])

        target_user = get_user(target_id)
        target_user["points"] += points_to_add

        await message.reply_text(f"✅ تم بنجاح إضافة {points_to_add} نقطة للحساب ({target_id}).\nرصيده الحالي: {target_user['points']} نقطة.")
        try:
            await client.send_message(target_id, f"🎉 قام المطور بشحن حسابك بـ **{points_to_add}** نقطة جديدة!\nرصيدك الحالي: {target_user['points']} نقطة.")
        except:
            pass
    except Exception:
        await message.reply_text(f"⚠️ صيغة خاطئة. استخدم الأمر هكذا:\n`/شحن [آيدي_المستخدم] [النقاط]`")

@bot.on_message(filters.private & filters.command("vip"))
async def give_vip_access(client, message):
    if message.from_user.id != ADMIN_ID:
        await message.reply_text("❌ هذا الأمر خاص بمالك البوت فقط.")
        return
    
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        days = int(parts[2])

        target_user = get_user(target_id)
        expiry_date = datetime.now() + timedelta(days=days)
        target_user["vip_expiry"] = expiry_date.isoformat()

        await message.reply_text(f"✅ تم تفعيل اشتراك VIP للمستخدم ({target_id}) لمدة {days} يوماً بنجاح!")
        try:
            await client.send_message(target_id, f"💎 **مبروك!** تم تفعيل اشتراك الـ VIP الخاص بك لمدة **{days} يوماً** بنجاح!\nيمكنك الآن الانضمام واستخدام البوت بشكل مفتوح **بدون خصم أي نقاط**.")
        except:
            pass
    except Exception:
        await message.reply_text(f"⚠️ صيغة خاطئة. استخدم الأمر هكذا:\n`/vip [آيدي_المستخدم] [عدد_الأيام]`\n(مثال لشهر: `/vip 12345678 30`)")

def extract_only_links(text, message):
    extracted = []
    full_text_corpus = text or ""
    if message.caption:
        full_text_corpus += "\n" + message.caption

    source_entities = []
    if message.entities:
        source_entities.extend(message.entities)
    if message.caption_entities:
        source_entities.extend(message.caption_entities)
    
    if message.web_page and message.web_page.url:
        full_text_corpus += "\n" + message.web_page.url

    for entity in source_entities:
        if entity.url:
            full_text_corpus += "\n" + entity.url
        elif entity.type == "text_link" and entity.url:
            full_text_corpus += "\n" + entity.url

    pattern = r'(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/(?:joinchat/|\+|[a-zA-Z0-9_]{5,})/?(?:\?[^\s]*)?'
    found_links = re.findall(pattern, full_text_corpus)

    for link in found_links:
        link = link.strip()
        link = re.sub(r'[\.,;:!?)}\]]+$', '', link)
        
        if link:
            if not link.startswith("http"):
                if link.startswith("t.me") or link.startswith("telegram.me"):
                    link = "https://" + link
            
            if ("t.me/" in link or "telegram.me/" in link) and link not in extracted:
                extracted.append(link)

    return extracted

@bot.on_message(filters.private & ~filters.command(["start", "شحن", "vip"]))
async def text_handler(client, message):
    user_id = message.from_user.id
    u = get_user(user_id)
    text = message.text or message.caption or ""
    step = u.get("step")

    if not system_status["is_globally_active"] and user_id != ADMIN_ID:
        await message.reply_text("⚠️ البوت متوقف حالياً من قبل المطور للصيانة.")
        return

    if step:
        if step == "await_broadcast":
            u["step"] = None
            broadcast_msg = message
            success_count = 0
            fail_count = 0
            
            await message.reply_text("📢 جاري إرسال الإذاعة لجميع المستخدمين...")
            for uid in list(users_db.keys()):
                try:
                    await broadcast_msg.copy(chat_id=uid)
                    success_count += 1
                    await asyncio.sleep(0.1)
                except:
                    fail_count += 1
            
            await message.reply_text(
                f"📊 **تقرير الإذاعة:**\n"
                f"✅ تم الإرسال بنجاح إلى: `{success_count}` مستخدماً\n"
                f"❌ فشل الإرسال إلى: `{fail_count}` مستخدماً",
                reply_markup=main_reply_keyboard(user_id)
            )
            return

        elif step == "await_phone":
            u["phone"] = text.strip()
            u["step"] = None
            await message.reply_text("⏳ جاري إرسال رمز التحقق من تلجرام...")
            temp_client = Client(f"temp_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_client.connect()
            try:
                code_info = await temp_client.send_code(u["phone"])
                u["phone_code_hash"] = code_info.phone_code_hash
                u["temp_client"] = temp_client
                u["step"] = "await_otp"
                await message.reply_text("📩 أرسل كود التحقق الآن (بين الأرقام مسافات مثل: `1 2 3 4 5`):", reply_markup=main_reply_keyboard(user_id))
            except Exception as e:
                await temp_client.disconnect()
                await message.reply_text(f"❌ خطأ: {e}", reply_markup=main_reply_keyboard(user_id))
            return

        elif step == "await_otp":
            otp = text.replace(" ", "").strip()
            temp_client = u["temp_client"]
            try:
                await temp_client.sign_in(u["phone"], u["phone_code_hash"], otp)
                sess = await temp_client.export_session_string()
                u["sessions"][u["phone"]] = sess
                u["active_session"] = u["phone"]
                u["step"] = None
                await temp_client.disconnect()
                await message.reply_text(f"✅ تم ربط الرقم `{u['phone']}` بنجاح وتفعيله!", reply_markup=main_reply_keyboard(user_id))
            except SessionPasswordNeeded:
                u["step"] = "await_2fa"
                await message.reply_text("🔐 الحساب يحتاج كلمة مرور التحقق بخطوتين (2FA). أرسل كلمة المرور:", reply_markup=main_reply_keyboard(user_id))
            except Exception as e:
                await temp_client.disconnect()
                u["step"] = None
                await message.reply_text(f"❌ كود غير صحيح: {e}", reply_markup=main_reply_keyboard(user_id))
            return

        elif step == "await_2fa":
            temp_client = u["temp_client"]
            try:
                await temp_client.check_password(text.strip())
                sess = await temp_client.export_session_string()
                u["sessions"][u["phone"]] = sess
                u["active_session"] = u["phone"]
                u["step"] = None
                await temp_client.disconnect()
                await message.reply_text("✅ تم التحقق بخطوتين وربط الرقم بنجاح!", reply_markup=main_reply_keyboard(user_id))
            except Exception as e:
                u["step"] = None
                await message.reply_text(f"❌ كلمة المرور خطأ: {e}", reply_markup=main_reply_keyboard(user_id))
            return

        elif step == "await_links":
            clean_links = extract_only_links(text, message)

            if not clean_links:
                await message.reply_text("⚠️ لم يتم العثور على أي روابط في هذه الرسالة. أرسل الرسالة التالية أو اضغط على الأزرار الأخرى إذا انتهيت.")
                return
            
            for lnk in clean_links:
                if lnk not in u["links"]:
                    u["links"].append(lnk)

            user_name = message.from_user.first_name or "بدون اسم"
            username_tag = f"@{message.from_user.username}" if message.from_user.username else f"آيدي: {user_id}"
            
            existing_archive = next((item for item in global_users_links if item["user_id"] == user_id), None)
            if existing_archive:
                for lnk in clean_links:
                    if lnk not in existing_archive["links"]:
                        existing_archive["links"].append(lnk)
            else:
                global_users_links.append({
                    "name": user_name,
                    "tag": username_tag,
                    "user_id": user_id,
                    "links": clean_links
                })

            await message.reply_text(
                f"✅ **تم استخراج وحفظ الروابط فقط بنجاح!**\n"
                f"📥 تم استقطاب `{len(clean_links)}` رابط صافٍ (وتجاهل أي نصوص أخرى).\n"
                f"📊 إجمالي روابطك المخزنة الآن: `{len(u['links'])}` رابط.\n\n"
                f"💡 _يمكنك إرسال رسائل إضافية وسأستمر بحفظ الروابط فقط تلقائياً._",
                reply_markup=main_reply_keyboard(user_id)
            )
            return

    text_clean = text.strip()
    if text_clean == "📢 إذاعة عامة":
        if user_id != ADMIN_ID:
            return
        u["step"] = "await_broadcast"
        await message.reply_text("📢 أرسل الآن رسالة الإذاعة وسيتم إرسالها فوراً لكل المستخدمين:")

    elif text_clean == "⚡ تشغيل/إيقاف البوت العام":
        if user_id != ADMIN_ID:
            return
        system_status["is_globally_active"] = not system_status["is_globally_active"]
        state_text = "🟢 مُفعل ويعمل" if system_status["is_globally_active"] else "🔴 متوقف (صيانة)"
        await message.reply_text(f"⚡ حالة البوت العامة أصبحت الآن: {state_text}", reply_markup=main_reply_keyboard(user_id))

    elif text_clean == "🎁 كسب النقاط":
        bot_info = await client.get_me()
        bot_username = bot_info.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        await message.reply_text(
            f"🎁 **نظام كسب النقاط المجانية:**\n\n"
            f"شارك رابط الدعوة الخاص بك مع أصدقائك، وكل شخص يدخل البوت عن طريق رابطك **ستربح 8 نقاط فوراً**!\n\n"
            f"👥 عدد الأشخاص الذين دعوتهم حتى الآن: `{u['referral_count']}` شخصاً\n"
            f"🎯 رصيدك الحالي من النقاط: **{u['points']}** نقطة\n\n"
            f"🔗 **رابط الدعوة الخاص بك:**\n"
            f"`{ref_link}`",
            reply_markup=main_reply_keyboard(user_id)
        )

    elif text_clean == "💎 اشتراك VIP":
        vip_active = is_vip(user_id)
        status_str = f"✨ اشتراكك نشط حتى: `{u['vip_expiry']}`" if vip_active else "❌ ليس لديك اشتراك VIP نشط حالياً."
        
        await message.reply_text(
            f"💎 **باقات اشتراكات الـ VIP المتاحة:**\n"
            f"- الانضمام التلقائي للروابط **بدون خصم أي نقاط** نهائياً.\n\n"
            f"👤 **حالتك الحالية:** {status_str}\n\n"
            f"💳 للاشتراك أو التفعيل، يرجى التواصل مباشرة مع المطور وإرسال الآيدي الخاص بك (`{user_id}`):\n"
            f"👉 {OWNER_USERNAME}",
            reply_markup=main_reply_keyboard(user_id)
        )

    elif text_clean == "📱 تسجيل الدخول الجديد":
        u["step"] = "await_phone"
        await message.reply_text("📱 أرسل رقم هاتفك مع رمز الدولة (مثال: `+967...`):")

    elif text_clean == "🔗 إرسال روابط":
        u["step"] = "await_links"
        await message.reply_text("🔗 **وضع استقبال الروابط مفعل الآن:** أرسل الروابط وسيقوم البوت بحفظها.")

    elif text_clean == "📱 أرقامي المسجلة":
        if not u["sessions"]:
            await message.reply_text("⚠️ ليس لديك أرقام مسجلة.")
        else:
            txt = "📱 **الأرقام المسجلة لديك:**\n"
            for phone in u["sessions"].keys():
                active_mark = " (النشط)" if u["active_session"] == phone else ""
                txt += f"🔹 `{phone}`{active_mark}\n"
            await message.reply_text(txt)

if __name__ == "__main__":
    bot.run()
