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
            "temp_links_buffer": [], 
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

# الأزرار العامة (بدون زر حفظ الروابط لتكون مرتبة)
def main_reply_keyboard(user_id):
    keyboard = [
        [KeyboardButton("📱 تسجيل الدخول الجديد"), KeyboardButton("🔗 إرسال روابط")],
        [KeyboardButton("🗑️ مسح الروابط"), KeyboardButton("🚀 بدء الانضمام")],
        [KeyboardButton("🛑 إيقاف الانضمام"), KeyboardButton("📱 أرقامي المسجلة")],
        [KeyboardButton("🗑️ حذف رقم مسجل"), KeyboardButton("⏱️ تحديد الوقت")],
        [KeyboardButton("💤 استراحة الروابط"), KeyboardButton("📊 حالة النظام")],
        [KeyboardButton("🎯 شحن نقاطك"), KeyboardButton("💎 اشتراك VIP")],
        [KeyboardButton("🎁 كسب النقاط")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("📢 إذاعة عامة"), KeyboardButton("⚡ تشغيل/إيقاف البوت العام")])
        keyboard.append([KeyboardButton("👁️‍🗨️ روابط المستخدمين (للمالك)"), KeyboardButton("🗑️ مسح أرشيف الروابط")])
        
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# لوحة مؤقتة تظهر فقط عند إرسال الروابط تحتوي على زر الحفظ
def links_mode_keyboard(user_id):
    keyboard = [
        [KeyboardButton("💾 حفظ الروابط المرسلة")],
        [KeyboardButton("🔙 إلغاء والعودة للرئيسية")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

bot = Client("my_ultimate_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.private & filters.command("start"))
async def start_cmd(client, message):
    user_id = message.from_user.id
    u = get_user(user_id)
    u["step"] = None  
    
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

    vip_status_text = "✨ مفعل (بدون خصم نقاط)" if is_vip(user_id) else "❌ غير مشترك"
    
    # رسالة ترحيب نظيفة وبسيطة بدون إزعاج ربح النقاط
    await message.reply_text(
        f"🎯 **مرحباً بك في لوحة تحكم اليوزر بوت!**\n\n"
        f"🆔 الآيدي الخاص بك: `{user_id}`\n"
        f"🎯 نقاطك الحالية: **{u['points']}** نقطة\n"
        f"💎 حالة اشتراك الـ VIP: **{vip_status_text}**\n\n"
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

async def run_auto_join(client, user_id, message):
    u = get_user(user_id)
    delay = u["settings"]["delay_min"]
    batch_limit = u["settings"]["batch_limit"]
    cooldown = u["settings"]["cooldown_mins"]

    active_ph = u["active_session"]
    sess_str = u["sessions"].get(active_ph)
    if not sess_str:
        u["is_running"] = False
        await message.reply_text("❌ لم يتم العثور على الجلسة النشطة للرقم.")
        return

    user_client = Client(f"session_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=sess_str, in_memory=True)
    try:
        await user_client.connect()
    except Exception as e:
        u["is_running"] = False
        await message.reply_text(f"❌ فشل الاتصال بالحساب: {e}")
        return

    joined_count = 0
    for link in list(u["links"]):
        if not u["is_running"]:
            break
        
        try:
            if "+" in link or "joinchat" in link:
                chat_hash = link.split("/")[-1].replace("+", "")
                await user_client.join_chat(chat_hash)
            else:
                channel_username = link.split("/")[-1]
                await user_client.join_chat(channel_username)
            
            joined_count += 1
            u["links"].remove(link)

            if not is_vip(user_id):
                u["points"] = max(0, u["points"] - 1)

            await asyncio.sleep(delay)

            if joined_count % batch_limit == 0 and len(u["links"]) > 0:
                await message.reply_text(f"💤 تم الانضمام إلى {joined_count} رابطاً. أخذ استراحة لمدة {cooldown} دقائق...")
                for _ in range(cooldown * 60):
                    if not u["is_running"]:
                        break
                    await asyncio.sleep(1)

        except UserAlreadyParticipant:
            u["links"].remove(link)
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
        except Exception as e:
            logger.error(f"Join error: {e}")

    await user_client.disconnect()
    u["is_running"] = False
    await message.reply_text(f"🏁 **انتهت عملية الانضمام!**\n📊 إجمالي ما تم الانضمام له: `{joined_count}` رابطاً.", reply_markup=main_reply_keyboard(user_id))


@bot.on_message(filters.private & ~filters.command(["start", "شحن", "vip"]))
async def text_handler(client, message):
    user_id = message.from_user.id
    u = get_user(user_id)
    text = message.text or message.caption or ""
    text_clean = text.strip()

    main_buttons = [
        "📱 تسجيل الدخول الجديد", "🔗 إرسال روابط", "💾 حفظ الروابط المرسلة", "🔙 إلغاء والعودة للرئيسية",
        "🗑️ مسح الروابط", "🚀 بدء الانضمام", "🛑 إيقاف الانضمام", 
        "📱 أرقامي المسجلة", "🗑️ حذف رقم مسجل", "⏱️ تحديد الوقت", 
        "💤 استراحة الروابط", "📊 حالة النظام", "🎯 شحن نقاطك", 
        "💎 اشتراك VIP", "🎁 كسب النقاط", "📢 إذاعة عامة", 
        "⚡ تشغيل/إيقاف البوت العام", "👁️‍🗨️ روابط المستخدمين (للمالك)", "🗑️ مسح أرشيف الروابط"
    ]

    if text_clean in main_buttons and text_clean != "💾 حفظ الروابط المرسلة":
        if text_clean != "🔗 إرسال روابط":
            u["step"] = None  

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
            
            await message.reply_text(f"📊 تم الإرسال إلى `{success_count}` مستخدماً.", reply_markup=main_reply_keyboard(user_id))
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
            # زر العودة أو الحفظ أثناء وضع الروابط
            if text_clean == "🔙 إلغاء والعودة للرئيسية":
                u["step"] = None
                u["temp_links_buffer"] = []
                await message.reply_text("↩️ تم إلغاء وضع الروابط.", reply_markup=main_reply_keyboard(user_id))
                return
            
            if text_clean == "💾 حفظ الروابط المرسلة":
                u["step"] = None
                if not u["temp_links_buffer"]:
                    await message.reply_text("⚠️ لم تقم بإرسال أي روابط جديدة لحفظها بعد.", reply_markup=links_mode_keyboard(user_id))
                    return
                
                added_count = 0
                for lnk in u["temp_links_buffer"]:
                    if lnk not in u["links"]:
                        u["links"].append(lnk)
                        added_count += 1
                
                u["temp_links_buffer"] = []
                await message.reply_text(
                    f"✅ **تم حفظ الروابط بنجاح!**\n"
                    f"📥 تم إضافة `{added_count}` رابطاً جديداً لقائمتك.\n"
                    f"📊 إجمالي روابطك المخزنة الآن: `{len(u['links'])}` رابط.",
                    reply_markup=main_reply_keyboard(user_id)
                )
                return

            # استقبال الروابط بصمت تام بدون أي رسائل مزعجة لكل رسالة
            clean_links = extract_only_links(text, message)
            if clean_links:
                for lnk in clean_links:
                    if lnk not in u["temp_links_buffer"]:
                        u["temp_links_buffer"].append(lnk)
            return

        elif step == "await_delay":
            u["step"] = None
            try:
                val = int(text.strip())
                u["settings"]["delay_min"] = val
                await message.reply_text(f"✅ تم تحديث وقت الانتظار بين الروابط إلى `{val}` ثانية.", reply_markup=main_reply_keyboard(user_id))
            except:
                await message.reply_text("⚠️ أرسل رقماً صحيحاً بالثواني.", reply_markup=main_reply_keyboard(user_id))
            return

        elif step == "await_batch":
            u["step"] = None
            try:
                parts = text.strip().split()
                batch_num = int(parts[0])
                cooldown_m = int(parts[1])
                u["settings"]["batch_limit"] = batch_num
                u["settings"]["cooldown_mins"] = cooldown_m
                await message.reply_text(f"✅ تم حفظ إعدادات الاستراحة (بعد كل {batch_num} روابط لمدة {cooldown_m} دقائق).", reply_markup=main_reply_keyboard(user_id))
            except:
                await message.reply_text("⚠️ صيغة خاطئة. مثال: `6 4`", reply_markup=main_reply_keyboard(user_id))
            return

        elif step == "await_delete_phone":
            u["step"] = None
            phone_to_del = text.strip()
            if phone_to_del in u["sessions"]:
                del u["sessions"][phone_to_del]
                if u["active_session"] == phone_to_del:
                    u["active_session"] = list(u["sessions"].keys())[0] if u["sessions"] else None
                await message.reply_text(f"✅ تم حذف الرقم `{phone_to_del}` بنجاح.", reply_markup=main_reply_keyboard(user_id))
            else:
                await message.reply_text("❌ هذا الرقم غير مسجل لديك.", reply_markup=main_reply_keyboard(user_id))
            return

    if text_clean == "📢 إذاعة عامة":
        if user_id != ADMIN_ID:
            return
        u["step"] = "await_broadcast"
        await message.reply_text("📢 أرسل الآن رسالة الإذاعة وسيتم إرسالها لكل المستخدمين:")

    elif text_clean == "⚡ تشغيل/إيقاف البوت العام":
        if user_id != ADMIN_ID:
            return
        system_status["is_globally_active"] = not system_status["is_globally_active"]
        state_text = "🟢 مُفعل ويعمل" if system_status["is_globally_active"] else "🔴 متوقف (صيانة)"
        await message.reply_text(f"⚡ حالة البوت العامة: {state_text}", reply_markup=main_reply_keyboard(user_id))

    elif text_clean == "🎁 كسب النقاط":
        bot_info = await client.get_me()
        bot_username = bot_info.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        await message.reply_text(
            f"🎁 **نظام كسب النقاط المجانية:**\n\n"
            f"شارك رابط الدعوة الخاص بك مع أصدقائك، وكل شخص يدخل البوت عبر رابطك **ستربح 8 نقاط فوراً**!\n\n"
            f"👥 عدد الأشخاص الذين دعوتهم: `{u['referral_count']}` شخصاً\n"
            f"🎯 رصيدك الحالي: **{u['points']}** نقطة\n\n"
            f"🔗 **رابط الدعوة الخاص بك:**\n`{ref_link}`",
            reply_markup=main_reply_keyboard(user_id)
        )

    elif text_clean == "💎 اشتراك VIP":
        vip_active = is_vip(user_id)
        status_str = f"✨ نشط حتى: `{u['vip_expiry']}`" if vip_active else "❌ غير مشترك حالياً."
        await message.reply_text(
            f"💎 **اشتراك VIP:**\n{status_str}\n\n"
            f"🆔 الآيدي الخاص بك: `{user_id}`\n"
            f"للاشتراكات تواصل مع المطور: {OWNER_USERNAME} وأرسل له الآيدي الخاص بك.",
            reply_markup=main_reply_keyboard(user_id)
        )

    elif text_clean == "📱 تسجيل الدخول الجديد":
        u["step"] = "await_phone"
        await message.reply_text("📱 أرسل رقم هاتفك مع رمز الدولة (مثال: `+96777xxxxxxx`):")

    elif text_clean == "🔗 إرسال روابط":
        u["temp_links_buffer"] = []  
        u["step"] = "await_links"
        # إظهار لوحة التحكم الخاصة بالروابط (يظهر فيها زر الحفظ فقط)
        await message.reply_text(
            "🔗 **وضع استقبال الروابط مفعل بصمت:**\n"
            "أرسل الآن كل الروابط أو الرسائل التي تريدها دفعة واحدة.\n"
            "عندما تنتهي تماماً، اضغط على زر **💾 حفظ الروابط المرسلة** بالأسفل.",
            reply_markup=links_mode_keyboard(user_id)
        )

    elif text_clean == "🗑️ مسح الروابط":
        u["links"] = []
        u["temp_links_buffer"] = []
        await message.reply_text("🗑️ تم مسح جميع روابطك المخزنة بنجاح.", reply_markup=main_reply_keyboard(user_id))

    elif text_clean == "🚀 بدء الانضمام":
        u["step"] = None
        if not u["active_session"] or u["active_session"] not in u["sessions"]:
            await message.reply_text("❌ يرجى تسجيل رقم وتفعيله أولاً.")
            return
        if not u["links"]:
            await message.reply_text("❌ لا توجد روابط مخزنة للانضمام إليها.")
            return
        if not is_vip(user_id) and u["points"] <= 0:
            await message.reply_text("❌ رصيدك من النقاط 0 وليس لديك اشتراك VIP.")
            return
        
        u["is_running"] = True
        await message.reply_text("🚀 بدأ الانضمام التلقائي للروابط...")
        asyncio.create_task(run_auto_join(client, user_id, message))

    elif text_clean == "🛑 إيقاف الانضمام":
        u["is_running"] = False
        await message.reply_text("🛑 تم إيقاف عملية الانضمام بنجاح.", reply_markup=main_reply_keyboard(user_id))

    elif text_clean == "📱 أرقامي المسجلة":
        if not u["sessions"]:
            await message.reply_text("⚠️ ليس لديك أرقام مسجلة.")
        else:
            txt = "📱 **الأرقام المسجلة لديك:**\n"
            for phone in u["sessions"].keys():
                active_mark = " (النشط)" if u["active_session"] == phone else ""
                txt += f"🔹 `{phone}`{active_mark}\n"
            await message.reply_text(txt, reply_markup=main_reply_keyboard(user_id))

    elif text_clean == "🗑️ حذف رقم مسجل":
        if not u["sessions"]:
            await message.reply_text("⚠️ ليس لديك أرقام مسجلة لحذفها.")
        else:
            u["step"] = "await_delete_phone"
            txt = "🗑️ أرسل رقم الهاتف الذي تريد حذفه من أرقامك المسجلة:\n"
            for phone in u["sessions"].keys():
                txt += f"🔹 `{phone}`\n"
            await message.reply_text(txt)

    elif text_clean == "⏱️ تحديد الوقت":
        u["step"] = "await_delay"
        await message.reply_text("⏱️ أرسل الآن عدد الثواني المطلوبة للانتظار بين كل رابط والانضمام الذي يليه (مثال: `5`):")

    elif text_clean == "💤 استراحة الروابط":
        u["step"] = "await_batch"
        await message.reply_text("💤 أرسل إعدادات الاستراحة بالصيغة التالية (عدد الروابط ثم مسافة ثم دقائق الاستراحة).\nمثال: `6 4` (يعني بعد كل 6 روابط يستريح 4 دقائق)")

    elif text_clean == "📊 حالة النظام":
        status_global = "🟢 يعمل" if system_status["is_globally_active"] else "🔴 متوقف للصيانة"
        await message.reply_text(
            f"📊 **حالة النظام:**\n"
            f"🆔 الآيدي الخاص بك: `{user_id}`\n"
            f"- حالة البوت العامة: {status_global}\n"
            f"- روابطك المخزنة حالياً: `{len(u['links'])}` رابط\n"
            f"- رصيدك من النقاط: `{u['points']}` نقطة",
            reply_markup=main_reply_keyboard(user_id)
        )

    elif text_clean == "🎯 شحن نقاطك":
        await message.reply_text(
            f"🎯 لشحن نقاطك، قم بدعوة أصدقائك عبر زر (كسب النقاط) أو تواصل مع المطور وأرسل له الآيدي الخاص بك (`{user_id}`):\n👉 {OWNER_USERNAME}",
            reply_markup=main_reply_keyboard(user_id)
        )

if __name__ == "__main__":
    bot.run()
