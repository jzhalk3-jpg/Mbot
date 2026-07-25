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
                "delay_secs": 5,      # الوقت بالثواني بين كل رابط
                "batch_limit": 5,     # ثابت على 5 روابط
                "cooldown_mins": 5    # وقت الاستراحة التلقائي
            },
            "is_running": False,
            "safe_mode": False        
        }
    return users_db[user_id]

def is_vip(user_id):
    if user_id == ADMIN_ID:
        return True  
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

# الأزرار العامة للمستخدمين العاديين
def main_reply_keyboard(user_id):
    keyboard = [
        [KeyboardButton("📱 تسجيل الدخول الجديد"), KeyboardButton("🔗 إرسال روابط")],
        [KeyboardButton("🗑️ مسح الروابط"), KeyboardButton("🚀 بدء الانضمام"), KeyboardButton("🛡️ انضمام ذكي وآمن (حماية الحظر)")],
        [KeyboardButton("🛑 إيقاف الانضمام"), KeyboardButton("📱 أرقامي المسجلة")],
        [KeyboardButton("🗑️ حذف رقم مسجل"), KeyboardButton("⏱️ تحديد وقت الثواني بين الروابط"), KeyboardButton("⏱️ تحديد وقت الاستراحة")],
        [KeyboardButton("📊 حالة النظام"), KeyboardButton("🎯 شحن نقاطك")],
        [KeyboardButton("💎 اشتراك VIP"), KeyboardButton("🎁 كسب النقاط")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("📢 إذاعة عامة"), KeyboardButton("⚡ تشغيل/إيقاف البوت العام")])
        keyboard.append([KeyboardButton("👁️‍🗨️ روابط المستخدمين (للمالك)"), KeyboardButton("🗑️ مسح أرشيف الروابط")])
        keyboard.append([KeyboardButton("⚡ شحن نقاط مستخدم (سريع)"), KeyboardButton("💎 تفعيل VIP مستخدم (سريع)")])
        
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# لوحة مؤقتة تظهر فقط عند إرسال الروابط
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

    vip_status_text = "✨ مفعل (دائم للمالك / بلا خصم)" if user_id == ADMIN_ID else ("✨ مفعل" if is_vip(user_id) else "❌ غير مشترك")
    points_display = "♾️ نقاط مفتوحة (مالك البوت)" if user_id == ADMIN_ID else f"**{u['points']}** نقطة"

    await message.reply_text(
        f"🎯 **مرحباً بك في لوحة تحكم اليوزر بوت!**\n\n"
        f"🆔 الآيدي الخاص بك: `{user_id}`\n"
        f"🎯 نقاطك الحالية: {points_display}\n"
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
    
    if u["safe_mode"]:
        delay = 10      
        batch_limit = 5 
        cooldown = 6    
    else:
        delay = u["settings"]["delay_secs"]  
        batch_limit = 5 
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
    links_queue = u["links"]

    mode_title = "🛡️ (الوضع الآمن الذكي لتفادي الحظر مفعل)" if u["safe_mode"] else "🚀 (الوضع العادي)"
    await message.reply_text(f"بدء عملية الانضمام {mode_title}...")

    while links_queue and u["is_running"]:
        link = links_queue[0]
        success_msg_type = None
        joined_successfully = False

        while not joined_successfully and u["is_running"]:
            try:
                if "+" in link or "joinchat" in link:
                    chat_hash = link.split("/")[-1].replace("+", "")
                    chat_obj = await user_client.join_chat(chat_hash)
                    if chat_obj and hasattr(chat_obj, "type") and str(chat_obj.type).lower().endswith("channel"):
                        success_msg_type = "تم الانضمام للقناة بنجاح"
                    else:
                        success_msg_type = "تم الانضمام للمجموعة بنجاح"
                    joined_successfully = True
                else:
                    target_entity = link.split("/")[-1]
                    try:
                        chat_obj = await user_client.join_chat(target_entity)
                        if chat_obj and hasattr(chat_obj, "type") and str(chat_obj.type).lower().endswith("channel"):
                            success_msg_type = "تم الانضمام للقناة بنجاح"
                        else:
                            success_msg_type = "تم الانضمام للمجموعة بنجاح"
                        joined_successfully = True
                    except Exception as join_err:
                        err_str = str(join_err)
                        if "USER_ALREADY_PARTICIPANT" in err_str:
                            success_msg_type = "تم الانضمام للمجموعة بنجاح"
                            joined_successfully = True
                        elif "INVITE_REQUEST_SENT" in err_str:
                            success_msg_type = "تم إرسال طلب الانضمام بنجاح"
                            joined_successfully = True
                        else:
                            # إذا كان ضغط تيليجرام (FloodWait)، نأخذ استراحة 5 دقائق (300 ثانية)
                            if "FLOOD_WAIT" in err_str:
                                await message.reply_text(f"⚠️ ضغط من تيليجرام. أخذ استراحة تلقائية لمدة 5 دقائق والمحاولة مجدداً...")
                                for _ in range(300):
                                    if not u["is_running"]:
                                        break
                                    await asyncio.sleep(1)
                                if not u["is_running"]:
                                    break
                                continue
                            else:
                                # أما إذا كان خطأ عادي في الرابط (مثل عدم توفره)، نتجاوزه فوراً لكي لا يتعطل البوت
                                success_msg_type = f"⚠️ تعذر الانضمام للرابط (تجاوز): {err_str}"
                                joined_successfully = True

            except UserAlreadyParticipant:
                success_msg_type = "تم الانضمام للمجموعة بنجاح"
                joined_successfully = True
            except FloodWait as fw:
                await message.reply_text(f"⚠️ ضغط مؤقت من تيليجرام (FloodWait). أخذ استراحة لمدة {fw.value} ثانية والمحاولة تلقائياً...")
                await asyncio.sleep(fw.value + 2)
            except Exception as e:
                err_str = str(e)
                if "FLOOD_WAIT" in err_str:
                    await message.reply_text(f"⚠️ ضغط من تيليجرام. أخذ استراحة تلقائية لمدة 5 دقائق وإعادة المحاولة...")
                    for _ in range(300):
                        if not u["is_running"]:
                            break
                        await asyncio.sleep(1)
                    if not u["is_running"]:
                        break
                    continue
                else:
                    success_msg_type = f"⚠️ خطأ في الرابط (تم التجاوز): {err_str}"
                    joined_successfully = True

        if not u["is_running"]:
            break

        links_queue.pop(0)
        joined_count += 1

        if user_id != ADMIN_ID and not is_vip(user_id):
            u["points"] = max(0, u["points"] - 1)

        points_label = "♾️ نقاط مفتوحة (مالك البوت)" if user_id == ADMIN_ID else f"`{u['points']}` نقطة"
        await message.reply_text(
            f"✅ **{success_msg_type}**\n"
            f"🔗 الرابط: `{link}`\n"
            f"🎯 نقاطك المتبقية: {points_label}\n"
            f"📊 الروابط المتبقية في الانتظار: `{len(links_queue)}`",
            disable_web_page_preview=True
        )

        for _ in range(delay):
            if not u["is_running"]:
                break
            await asyncio.sleep(1)

        if joined_count % batch_limit == 0 and len(links_queue) > 0:
            await message.reply_text(f"💤 تم الانضمام إلى {joined_count} رابطاً. أخذ استراحة لمدة {cooldown} دقائق لحماية الرقم...")
            for _ in range(cooldown * 60):
                if not u["is_running"]:
                    break
                await asyncio.sleep(1)

    await user_client.disconnect()
    u["is_running"] = False
    await message.reply_text(f"🏁 **انتهت عملية الانضمام!**\n📊 إجمالي ما تم إنجازه بنجاح: `{joined_count}` رابطاً.", reply_markup=main_reply_keyboard(user_id))


@bot.on_message(filters.private & ~filters.command(["start", "شحن", "vip"]))
async def text_handler(client, message):
    user_id = message.from_user.id
    u = get_user(user_id)
    text = message.text or message.caption or ""
    text_clean = text.strip()

    main_buttons = [
        "📱 تسجيل الدخول الجديد", "🔗 إرسال روابط", "💾 حفظ الروابط المرسلة", "🔙 إلغاء والعودة للرئيسية",
        "🗑️ مسح الروابط", "🚀 بدء الانضمام", "🛡️ انضمام ذكي وآمن (حماية الحظر)", "🛑 إيقاف الانضمام", 
        "📱 أرقامي المسجلة", "🗑️ حذف رقم مسجل", "⏱️ تحديد وقت الثواني بين الروابط", "⏱️ تحديد وقت الاستراحة", 
        "📊 حالة النظام", "🎯 شحن نقاطك", "💎 اشتراك VIP", "🎁 كسب النقاط", 
        "📢 إذاعة عامة", "⚡ تشغيل/إيقاف البوت العام", "👁️‍🗨️ روابط المستخدمين (للمالك)", "🗑️ مسح أرشيف الروابط",
        "⚡ شحن نقاط مستخدم (سريع)", "💎 تفعيل VIP مستخدم (سريع)"
    ]

    if text_clean in main_buttons and text_clean not in ["💾 حفظ الروابط المرسلة", "🔙 إلغاء والعودة للرئيسية"]:
        if text_clean not in ["🔗 إرسال روابط", "👁️‍🗨️ روابط المستخدمين (للمالك)"]:
            u["step"] = None  

    step = u.get("step")

    if not system_status["is_globally_active"] and user_id != ADMIN_ID:
        await message.reply_text("⚠️ البوت متوقف حالياً من قبل المطور للصيانة.")
        return

    if text_clean == "🔙 إلغاء والعودة للرئيسية":
        u["step"] = None
        u["temp_links_buffer"] = []
        await message.reply_text("↩️ تم الإلغاء والعودة للقائمة الرئيسية.", reply_markup=main_reply_keyboard(user_id))
        return

    if step:
        if step == "await_broadcast":
            u["step"] = None
            broadcast_msg = message
            success_count = 0
            
            await message.reply_text("📢 جاري إرسال الإذاعة لجميع المستخدمين...")
            for uid in list(users_db.keys()):
                try:
                    await broadcast_msg.copy(chat_id=uid)
                    success_count += 1
                    await asyncio.sleep(0.1)
                except:
                    pass
            
            await message.reply_text(f"📊 تم الإرسال إلى `{success_count}` مستخدماً.", reply_markup=main_reply_keyboard(user_id))
            return

        elif step == "await_admin_charge":
            u["step"] = None
            try:
                parts = text.split()
                target_id = int(parts[0])
                pts = int(parts[1])
                target_user = get_user(target_id)
                target_user["points"] += pts
                await message.reply_text(f"✅ تم إضافة `{pts}` نقطة للمستخدم `{target_id}` بنجاح.\nرصيده الحالي: `{target_user['points']}` نقطة.", reply_markup=main_reply_keyboard(user_id))
                try:
                    await client.send_message(target_id, f"🎉 قام المطور بشحن حسابك بـ **{pts}** نقطة جديدة!\nرصيدك الحالي: **{target_user['points']}** نقطة.")
                except:
                    pass
            except:
                await message.reply_text("⚠️ صيغة خاطئة. أرسل هكذا مثلاً: `123456789 50`", reply_markup=main_reply_keyboard(user_id))
            return

        elif step == "await_admin_vip":
            u["step"] = None
            try:
                parts = text.split()
                target_id = int(parts[0])
                days = int(parts[1])
                target_user = get_user(target_id)
                expiry_date = datetime.now() + timedelta(days=days)
                target_user["vip_expiry"] = expiry_date.isoformat()
                await message.reply_text(f"✅ تم تفعيل VIP للمستخدم `{target_id}` لمدة `{days}` يوماً بنجاح.", reply_markup=main_reply_keyboard(user_id))
                try:
                    await client.send_message(target_id, f"💎 **مبروك!** تم تفعيل اشتراك الـ VIP الخاص بك لمدة **{days} يوماً** بنجاح!")
                except:
                    pass
            except:
                await message.reply_text("⚠️ صيغة خاطئة. أرسل هكذا مثلاً: `123456789 30`", reply_markup=main_reply_keyboard(user_id))
            return

        elif step == "await_view_user_links":
            u["step"] = None
            try:
                target_id = int(text.strip())
                if target_id in users_db:
                    t_user = users_db[target_id]
                    links_list = t_user["links"]
                    if not links_list:
                        await message.reply_text(f"⚠️ المستخدم `{target_id}` ليس لديه أي روابط مخزنة حالياً.", reply_markup=main_reply_keyboard(user_id))
                    else:
                        txt = f"👁️‍🗨️ **روابط المستخدم (`{target_id}`):** (إجمالي: {len(links_list)})\n\n"
                        for idx, lk in enumerate(links_list[:30], 1):
                            txt += f"{idx}. `{lk}`\n"
                        if len(links_list) > 30:
                            txt += f"\n... و {len(links_list) - 30} رابطاً إضافياً."
                        await message.reply_text(txt, reply_markup=main_reply_keyboard(user_id))
                else:
                    await message.reply_text("❌ هذا الآيدي غير موجود في قاعدة بيانات المستخدمين.", reply_markup=main_reply_keyboard(user_id))
            except:
                await message.reply_text("⚠️ أرسل آيدي صحيحاً بالأرقام.", reply_markup=main_reply_keyboard(user_id))
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

            clean_links = extract_only_links(text, message)
            if clean_links:
                for lnk in clean_links:
                    if lnk not in u["temp_links_buffer"]:
                        u["temp_links_buffer"].append(lnk)
            return

        elif step == "await_delay_secs":
            u["step"] = None
            try:
                delay_s = int(text.strip())
                u["settings"]["delay_secs"] = delay_s
                await message.reply_text(f"✅ تم تحديد وقت الانتظار بين كل رابط بـ `{delay_s}` ثوانٍ بنجاح.", reply_markup=main_reply_keyboard(user_id))
            except:
                await message.reply_text("⚠️ أرسل رقماً صحيحاً يمثل عدد الثواني (مثال: `5`).", reply_markup=main_reply_keyboard(user_id))
            return

        elif step == "await_cooldown_only":
            u["step"] = None
            try:
                cooldown_m = int(text.strip())
                u["settings"]["batch_limit"] = 5  
                u["settings"]["cooldown_mins"] = cooldown_m
                await message.reply_text(f"✅ تم ضبط وقت الاستراحة التلقائي بنجاح (بعد كل 5 روابط سيستريح لمدة `{cooldown_m}` دقائق).", reply_markup=main_reply_keyboard(user_id))
            except:
                await message.reply_text("⚠️ أرسل رقماً صحيحاً يمثل عدد الدقائق (مثال: `5`).", reply_markup=main_reply_keyboard(user_id))
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

    elif text_clean == "⚡ شحن نقاط مستخدم (سريع)":
        if user_id != ADMIN_ID:
            return
        u["step"] = "await_admin_charge"
        await message.reply_text("⚡ أرسل الآيدي وعدد النقاط بهذه الصيغة:\n`[آيدي_المستخدم] [عدد_النقاط]`\n(مثال: `123456789 50`)")

    elif text_clean == "💎 تفعيل VIP مستخدم (سريع)":
        if user_id != ADMIN_ID:
            return
        u["step"] = "await_admin_vip"
        await message.reply_text("💎 أرسل آيدي المستخدم وعدد الأيام بهذه الصيغة:\n`[آيدي_المستخدم] [عدد_الأيام]`\n(مثال: `123456789 30`)")

    elif text_clean == "👁️‍🗨️ روابط المستخدمين (للمالك)":
        if user_id != ADMIN_ID:
            return
        if not users_db:
            await message.reply_text("⚠️ لا يوجد أي مستخدمين مسجلين في البوت حتى الآن.", reply_markup=main_reply_keyboard(user_id))
            return
        
        txt = "👁️‍🗨️ **قائمة المستخدمين والروابط المخزنة:**\n\n"
        for uid, dat in users_db.items():
            txt += f"👤 آيدي: `{uid}`\n- عدد الروابط: `{len(dat['links'])}` رابط\n- النقاط: `{dat['points']}`\n------------------\n"
        
        u["step"] = "await_view_user_links"
        await message.reply_text(txt + "\n📥 **أرسل الآن آيدي المستخدم** الذي تريد استعراض وسحب كل روابطه المخزنة:", reply_markup=main_reply_keyboard(user_id))

    elif text_clean == "🗑️ مسح أرشيف الروابط":
        if user_id != ADMIN_ID:
            return
        count_cleared = 0
        for uid in users_db:
            count_cleared += len(users_db[uid]["links"])
            users_db[uid]["links"] = []
        await message.reply_text(f"🗑️ تم مسح أرشيف الروابط لكل المستخدمين بنجاح (تم مسح `{count_cleared}` رابطاً).", reply_markup=main_reply_keyboard(user_id))

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
        status_str = "✨ نشط دائماً (مالك البوت)" if user_id == ADMIN_ID else (f"✨ نشط حتى: `{u['vip_expiry']}`" if vip_active else "❌ غير مشترك حالياً.")
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
        await message.reply_text(
            "🔗 **وضع استقبال الروابط مفعل بصمت:**\n"
            "أرسل الآن رسالة واحدة تحتوي على عدة روابط، أو أرسل عدة رسائل كما تحب.\n"
            "عندما تنتهي تماماً، اضغط على زر **💾 حفظ الروابط المرسلة** بالأسفل ليتم حفظ الكل دفعة واحدة.",
            reply_markup=links_mode_keyboard(user_id)
        )

    elif text_clean == "🗑️ مسح الروابط":
        u["links"] = []
        u["temp_links_buffer"] = []
        await message.reply_text("🗑️ تم مسح جميع روابطك المخزنة بنجاح.", reply_markup=main_reply_keyboard(user_id))

    elif text_clean == "🚀 بدء الانضمام":
        u["safe_mode"] = False
        u["step"] = None
        if not u["active_session"] or u["active_session"] not in u["sessions"]:
            await message.reply_text("❌ يرجى تسجيل رقم وتفعيله أولاً.")
            return
        if not u["links"]:
            await message.reply_text("❌ لا توجد روابط مخزنة للانضمام إليها.")
            return
        if user_id != ADMIN_ID and not is_vip(user_id) and u["points"] <= 0:
            await message.reply_text("❌ رصيدك من النقاط 0 وليس لديك اشتراك VIP.")
            return
        
        u["is_running"] = True
        await message.reply_text("🚀 بدأ الانضمام التلقائي بالوضع العادي...")
        asyncio.create_task(run_auto_join(client, user_id, message))

    elif text_clean == "🛡️ انضمام ذكي وآمن (حماية الحظر)":
        u["safe_mode"] = True
        u["step"] = None
        if not u["active_session"] or u["active_session"] not in u["sessions"]:
            await message.reply_text("❌ يرجى تسجيل رقم وتفعيله أولاً.")
            return
        if not u["links"]:
            await message.reply_text("❌ لا توجد روابط مخزنة للانضمام إليها.")
            return
        if user_id != ADMIN_ID and not is_vip(user_id) and u["points"] <= 0:
            await message.reply_text("❌ رصيدك من النقاط 0 وليس لديك اشتراك VIP.")
            return
        
        u["is_running"] = True
        await message.reply_text("🛡️ **تم تفعيل وضع الانضمام الذكي والآمن:**\nالبوت سيتولى ضبط التوقيتات والفواصل تلقائياً لحماية رقمك من الحظر تماماً.")
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

    elif text_clean == "⏱️ تحديد وقت الثواني بين الروابط":
        u["step"] = "await_delay_secs"
        await message.reply_text("⏱️ أرسل الآن **عدد الثواني** التي تريدها بين كل رابط والرابط الذي يليه (مثال: `5`):")

    elif text_clean == "⏱️ تحديد وقت الاستراحة":
        u["step"] = "await_cooldown_only"
        await message.reply_text("⏱️ أرسل الآن **وقت الاستراحة بالدقائق فقط** (مثال: `5` يعني بعد كل 5 روابط سيستريح البوت المدة التي تحددها):")

    elif text_clean == "📊 حالة النظام":
        status_global = "🟢 يعمل" if system_status["is_globally_active"] else "🔴 متوقف للصيانة"
        points_txt = "♾️ نقاط مفتوحة (مالك)" if user_id == ADMIN_ID else f"`{u['points']}` نقطة"
        await message.reply_text(
            f"📊 **حالة النظام:**\n"
            f"🆔 الآيدي الخاص بك: `{user_id}`\n"
            f"- حالة البوت العامة: {status_global}\n"
            f"- روابطك المخزنة حالياً: `{len(u['links'])}` رابط\n"
            f"- رصيدك من النقاط: {points_txt}",
            reply_markup=main_reply_keyboard(user_id)
        )

    elif text_clean == "🎯 شحن نقاطك":
        await message.reply_text(
            f"🎯 لشحن نقاطك، تواصل مع مالك البوت وأرسل له الآيدي الخاص بك (`{user_id}`):\n👉 {OWNER_USERNAME}",
            reply_markup=main_reply_keyboard(user_id)
        )

if __name__ == "__main__":
    bot.run()
