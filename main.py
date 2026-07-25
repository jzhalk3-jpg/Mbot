import asyncio
import logging
import re
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import BOT_TOKEN, API_ID, API_HASH, ADMIN_ID
from database import init_db, get_connection
from keyboards import get_main_keyboard

logging.basicConfig(level=logging.INFO)
init_db()

running_states = {}

def extract_all_links_robust(text):
    if not text:
        return []
    # تعبير منظم قوي وشامل جداً لالتقاط كافة روابط تيليجرام العامة والخاصة وبأي كمية
    pattern = r'(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/(?:joinchat/|\+|c/|[a-zA-Z0-9_]{5,})/?(?:[0-9]+)?/?(?:\?[^\s]*)?'
    found_links = re.findall(pattern, text)
    extracted = []
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

async def join_logic(session_str, link):
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    try:
        await client.connect()
        target_entity = None
        is_request_join = False
        
        if "joinchat" in link or "+" in link:
            hash_val = link.split("/")[-1].replace("+", "").strip()
            try:
                result = await client(functions.messages.ImportChatInviteRequest(hash=hash_val))
                if hasattr(result, 'chats') and result.chats:
                    target_entity = result.chats[0]
            except Exception as e:
                err_str = str(e).lower()
                if "flood" in err_str or "wait" in err_str or "seconds" in err_str:
                    return "RESTRICTED", f"⏳ الحساب مقيد مؤقتاً: {str(e)}"
                try:
                    res_check = await client(functions.messages.CheckChatInviteRequest(hash=hash_val))
                    is_request_join = True
                    return "SUCCESS_REQUEST", "⏳ تم إرسال طلب الانضمام وبانتظار الموافقة!"
                except Exception as inner_e:
                    if "alreadyinchannel" in str(inner_e).lower() or "user_already_participant" in str(inner_e).lower():
                        target_entity = await client.get_entity(link)
                    else:
                        raise inner_e
        else:
            clean_link = link.split("/")[-1].strip()
            try:
                result = await client(functions.channels.JoinChannelRequest(clean_link))
                target_entity = await client.get_entity(clean_link)
            except Exception as e:
                err_str = str(e).lower()
                if "flood" in err_str or "wait" in err_str or "seconds" in err_str:
                    return "RESTRICTED", f"⏳ الحساب مقيد مؤقتاً: {str(e)}"
                if "requested to join" in err_str:
                    return "SUCCESS_REQUEST", "⏳ تم إرسال طلب الانضمام بانتظار الموافقة!"
                target_entity = await client.get_entity(clean_link)
                await client(functions.channels.JoinChannelRequest(channel=target_entity))

        verified = False
        if target_entity and not is_request_join:
            await asyncio.sleep(3) 
            try:
                async for message in client.iter_messages(target_entity, limit=5):
                    if message.reply_markup and hasattr(message.reply_markup, 'rows'):
                        for row in message.reply_markup.rows:
                            for button in row.buttons:
                                if any(w in button.text.lower() for w in ["إنسان", "انسان", "أنا", "لست", "robot", "human", "verify", "تحقق"]):
                                    await message.click(data=button.data)
                                    await asyncio.sleep(1)
                                    verified = True
            except Exception:
                pass

        if is_request_join:
            return "SUCCESS", "⏳ تم إرسال طلب الانضمام بنجاح"
            
        verify_str = " وتم التحقق بنجاح" if verified else ""
        return "SUCCESS", f"✅ تم الانضمام{verify_str}"
                    
    except Exception as e:
        err_str = str(e).lower()
        if "alreadyinchannel" in err_str or "user_already_participant" in err_str: 
            return "SUCCESS", "✅ تم الانضمام مسبقاً"
        if "channelstoomuch" in err_str: 
            return "FAILED", "❌ الحساب ممتلئ قنوات!"
        if "flood" in err_str or "wait" in err_str:
            return "RESTRICTED", f"⏳ الحساب مقيد مؤقتاً: {str(e)}"
        return "FAILED", f"❌ فشل: {str(e)}"
    finally:
        await client.disconnect()

async def background_task(user_id, context, active_acc, delay_time, rest_time_minutes, links):
    try:
        join_counter = 0
        db = get_connection()
        cursor = db.cursor()

        await context.bot.send_message(chat_id=user_id, text=f"🚀 تم التحقق من النقاط وإطلاق مهمتك بنجاح لـ {len(links)} رابط في الخلفية بالتوازي!")

        for lid, link in links:
            if not running_states.get(user_id): break
            
            if user_id != ADMIN_ID:
                cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
                row_bal = cursor.fetchone()
                if row_bal and row_bal[0] < 1:
                    await context.bot.send_message(chat_id=user_id, text="⚠️ عذراً، نفدت نقاطك المتاحة. يرجى شحن نقاطك للمتابعة.")
                    break

            if join_counter > 0 and join_counter % 5 == 0:
                await context.bot.send_message(chat_id=user_id, text=f"⏳ تم الانضمام لـ 5 روابط بنجاح. البوت يدخل الآن في استراحة لمدة {rest_time_minutes} دقائق...")
                for _ in range(int(rest_time_minutes * 60 * 10)):
                    if not running_states.get(user_id): break
                    await asyncio.sleep(0.1)
                if not running_states.get(user_id): break
                await context.bot.send_message(chat_id=user_id, text="🚀 انتهت الاستراحة المحددة، جاري استئناف العمل...")
            
            while True:
                if not running_states.get(user_id): break
                status, msg = await join_logic(active_acc[0], link)
                
                if status == "RESTRICTED":
                    await context.bot.send_message(chat_id=user_id, text=f"⚠️ تفاجأنا بطلب انتظار من تليجرام لحسابك.\n⏳ الحساب مقيد حالياً. سأدخل في استراحة أمان لمدة 5 دقائق كاملة، ثم سأعيد المحاولة تلقائياً على نفس الرابط دون توقف: {link}")
                    for _ in range(300 * 10):
                        if not running_states.get(user_id): break
                        await asyncio.sleep(0.1)
                    await context.bot.send_message(chat_id=user_id, text=f"🔄 انتهت الـ 5 دقائق، جاري إعادة محاولة الانضمام للرابط الحالي الآن...")
                    continue
                
                cursor.execute("UPDATE links SET status=? WHERE id=?", ('completed' if "SUCCESS" in status else 'failed', lid))
                if user_id != ADMIN_ID:
                    cursor.execute("UPDATE users SET balance = balance - 1 WHERE user_id=?", (user_id,))
                db.commit()
                
                join_counter += 1
                cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
                rem_bal = cursor.fetchone()[0]
                bal_str = "المشرف (نقاط مفتوحة)" if user_id == ADMIN_ID else f"{rem_bal} نقطة"
                
                # تنسيق شكل التقرير المطابق لبوتك القديم تماماً
                clean_target = link.split("?")[0].rstrip("/")
                parts_path = clean_target.split("/")
                if len(parts_path) >= 4 and parts_path[-1].isdigit() and not "joinchat" in link and not "/c/" in link:
                    display_link_id = parts_path[-2]
                elif "+" in link or "joinchat" in link:
                    display_link_id = "+" + link.split("/")[-1].replace("+", "")
                else:
                    display_link_id = parts_path[-1]

                await context.bot.send_message(
                    chat_id=user_id, 
                    text=f"📱 الرقم: {active_acc[1]}\n🔗 الرابط: {display_link_id}\nالنتيجة: {msg}\n🎯 نقاطك المتبقية: {bal_str}"
                )
                break
            
            for _ in range(int(delay_time * 10)):
                if not running_states.get(user_id): break
                await asyncio.sleep(0.1)
        
        await context.bot.send_message(chat_id=user_id, text=f"🏁 انتهى الإرسال بنجاح!\n✅ تم إنجاز إجمالي عدد: ({join_counter}) رابط داخل قائمة الانتظار الخاصة بك بنجاح تام.")
        db.close()
    except Exception as e:
        logging.error(f"Task error: {e}")
    finally:
        running_states[user_id] = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    db = get_connection()
    cursor = db.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    db.commit()
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]
    db.close()
    
    context.user_data.clear()
    balance_display = "المشرف العام (نقاط مفتوحة)" if user_id == ADMIN_ID else f"{balance} نقطة"
    
    await update.message.reply_text(
        f"👋 مرحباً بك يا {name} في نظام الانضمام الذكي.\n\n"
        f"يمكنك إدارة حسابات تيليجرام، إضافة الروابط، وتشغيل الانضمام التلقائي بسهولة.\n\n"
        f"💳 **معرف حسابك:** `{user_id}`\n"
        f"🎯 **رصيدك الحالي:** {balance_display}\n\n"
        f"اختر الخدمة التي تريدها من القائمة:", 
        reply_markup=get_main_keyboard(user_id, ADMIN_ID),
        parse_mode="Markdown"
    )

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    action = context.user_data.get('action')
    
    db = get_connection()
    cursor = db.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    db.commit()
    
    if text == "/start":
        db.close()
        return await start(update, context)

    if text == "💎 شحن النقاط":
        db.close()
        keyboard = [[InlineKeyboardButton("📩 التواصل مع الدعم", url="https://t.me/Ra11_8h")]]
        await update.message.reply_text(
            f"💎 **شحن النقاط**\n\n"
            f"لشراء أو شحن نقاط جديدة يرجى التواصل مع الدعم.\n\n"
            f"👤 **معرف المسؤول:**\n@Ra11_8h\n\n"
            f"أرسل له معرف حسابك داخل البوت وسيتم شحن رصيدك مباشرة:\n`{user_id}`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # 🔗 إرسال روابط (وضع الإرسال المفتوح والصامت)
    if text == "🔗 إرسال روابط":
        db.close()
        context.user_data['action'] = 'add_links'
        context.user_data['temp_links_list'] = []
        await update.message.reply_text(
            "📥 وضع الإرسال المفتوح والصامت نشط الآن!\n"
            "قم بنسخ ولصق كافة الرسائل والروابط التي لديك هنا تباعاً وبأي عدد تريد.\n\n"
            "📥 عند انتهائك تماماً من إرسال كل شيء، اضغط على زر **(📥 حفظ الروابط وإنهاء الإرسال)** بالأسفل ليظهر لك التقرير النهائي.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📥 حفظ الروابط وإنهاء الإرسال")], [KeyboardButton("🔙 إلغاء والعودة للرئيسية")]], resize_keyboard=True)
        )
        return

    if text == "🔙 إلغاء والعودة للرئيسية":
        db.close()
        context.user_data.clear()
        await update.message.reply_text("↩️ تم الإلغاء والعودة للقائمة الرئيسية.", reply_markup=get_main_keyboard(user_id, ADMIN_ID))
        return

    if text == "📥 حفظ الروابط وإنهاء الإرسال" and action == 'add_links':
        temp_links = context.user_data.get('temp_links_list', [])
        if temp_links:
            for l in temp_links:
                cursor.execute("INSERT INTO links (user_id, link) VALUES (?, ?)", (user_id, l))
            db.commit()
            total_saved = len(temp_links)
            db.close()
            context.user_data.clear()
            await update.message.reply_text(
                f"🏁 انتهى الإرسال بنجاح!\n"
                f"✅ تم حفظ إجمالي عدد: ({total_saved}) رابط داخل قائمة الانتظار الخاصة بك بنجاح تام.",
                reply_markup=get_main_keyboard(user_id, ADMIN_ID)
            )
        else:
            db.close()
            await update.message.reply_text("⚠️ لم تقم بإرسال أي روابط لحفظها.")
        return

    if action == 'add_links':
        found = extract_all_links_robust(text)
        if found:
            temp_list = context.user_data.setdefault('temp_links_list', [])
            for f_link in found:
                if f_link not in temp_list:
                    temp_list.append(f_link)
        return

    # 🗑️ مسح الروابط
    if text == "🗑️ مسح الروابط":
        cursor.execute("DELETE FROM links WHERE user_id=?", (user_id,))
        db.commit()
        db.close()
        await update.message.reply_text("🗑️ تم مسح جميع روابطك بنجاح.")
        return

    # 📱 تسجيل الدخول الجديد
    if text == "📱 تسجيل الدخول الجديد":
        db.close()
        context.user_data['action'] = 'waiting_phone'
        await update.message.reply_text(
            "📱 **تسجيل حساب جديد**\n\n"
            "الرجاء إرسال رقم الهاتف مع رمز الدولة (مثال: `+9665xxxxxxxx`):",
            parse_mode="Markdown"
        )
        return

    if action == 'waiting_phone':
        phone = text
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        try:
            sent = await client.send_code_request(phone)
            context.user_data['phone'] = phone
            context.user_data['phone_code_hash'] = sent.phone_code_hash
            context.user_data['client_session'] = client
            context.user_data['action'] = 'waiting_code'
            db.close()
            await update.message.reply_text("📩 تم إرسال رمز التحقق إلى حسابك في تيليجرام.\nالرجاء إرسال الرمز هنا (افصل بين الأرقام بمسافات إن أمكن أو اكتبه مباشرة):")
        except Exception as e:
            db.close()
            await update.message.reply_text(f"❌ حدث خطأ أثناء إرسال الكود: {e}")
            context.user_data.clear()
        return

    if action == 'waiting_code':
        code = text.replace(" ", "")
        phone = context.user_data.get('phone')
        phone_code_hash = context.user_data.get('phone_code_hash')
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            session_string = client.session.save()
            
            cursor.execute("UPDATE accounts SET is_active=0 WHERE user_id=?", (user_id,))
            cursor.execute("INSERT INTO accounts (user_id, session, phone, is_active) VALUES (?, ?, ?, 1)", (user_id, session_string, phone))
            db.commit()
            db.close()
            
            await update.message.reply_text("✅ تم تسجيل الدخول وتفعيل الرقم بنجاح تام!", reply_markup=get_main_keyboard(user_id, ADMIN_ID))
            context.user_data.clear()
        except Exception as e:
            db.close()
            if "2FA" in str(e) or "Password" in str(e):
                context.user_data['action'] = 'waiting_2fa'
                await update.message.reply_text("🔒 الحساب محمي التحقق بخطوتين (كلمة المرور).\nالرجاء إرسال كلمة المرور الآن:")
            else:
                await update.message.reply_text(f"❌ الكود غير صحيح أو حدث خطأ: {e}")
        return

    if action == 'waiting_2fa':
        password = text
        phone = context.user_data.get('phone')
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        try:
            await client.sign_in(password=password)
            session_string = client.session.save()
            
            cursor.execute("UPDATE accounts SET is_active=0 WHERE user_id=?", (user_id,))
            cursor.execute("INSERT INTO accounts (user_id, session, phone, is_active) VALUES (?, ?, ?, 1)", (user_id, session_string, phone))
            db.commit()
            db.close()
            
            await update.message.reply_text("✅ تم التحقق بكلمة المرور وتفعيل الحساب بنجاح!", reply_markup=get_main_keyboard(user_id, ADMIN_ID))
            context.user_data.clear()
        except Exception as e:
            db.close()
            await update.message.reply_text(f"❌ كلمة المرور غير صحيحة: {e}")
        return

    if text == "📱 أرقامي المسجلة":
        cursor.execute("SELECT id, phone, is_active FROM accounts WHERE user_id=?", (user_id,))
        accs = cursor.fetchall()
        db.close()
        if not accs:
            return await update.message.reply_text("⚠️ لا توجد أرقام مسجلة لديك.")
        msg = "📱 **أرقامك المسجلة:**\n\n"
        for aid, ph, active in accs:
            status = "🟢 (مفعل حالياً)" if active == 1 else "⚪ (غير مفعل)"
            msg += f"• الرقم: `{ph}` -- {status}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    if text == "🗑️ حذف رقم مسجل":
        cursor.execute("SELECT id, phone FROM accounts WHERE user_id=?", (user_id,))
        accs = cursor.fetchall()
        db.close()
        if not accs:
            return await update.message.reply_text("⚠️ لا توجد أرقام لحذفها.")
        keyboard = [[InlineKeyboardButton(f"حذف: {ph}", callback_data=f"del_acc_{aid}")] for aid, ph in accs]
        await update.message.reply_text("اختر الرقم الذي تريد حذفه:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if text == "📊 حالة النظام":
        cursor.execute("SELECT COUNT(*) FROM links WHERE user_id=? AND status='pending'", (user_id,))
        pending_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM links WHERE user_id=? AND status='completed'", (user_id,))
        completed_count = cursor.fetchone()[0]
        cursor.execute("SELECT phone FROM accounts WHERE user_id=? AND is_active=1", (user_id,))
        active_acc = cursor.fetchone()
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        bal = cursor.fetchone()[0]
        db.close()
        
        act_ph = active_acc[0] if active_acc else "لا يوجد"
        bal_str = "المشرف (مفتوح)" if user_id == ADMIN_ID else f"{bal} نقطة"
        
        await update.message.reply_text(
            f"📊 **حالة النظام الخاصة بك:**\n\n"
            f"📱 الرقم المفعل: `{act_ph}`\n"
            f"🔗 روابط بالانتظار: {pending_count}\n"
            f"✅ روابط اكتملت: {completed_count}\n"
            f"🎯 رصيدك: {bal_str}",
            parse_mode="Markdown"
        )
        return

    if text == "⏱️ الوقت بين الانضمامات":
        db.close()
        context.user_data['action'] = 'set_delay'
        await update.message.reply_text("⏱️ أرسل الآن عدد الثواني المطلوبة للانتظار بين كل عملية انضمام (مثال: `10`):")
        return

    if action == 'set_delay':
        try:
            d_val = int(text)
            cursor.execute("UPDATE users SET delay=? WHERE user_id=?", (d_val, user_id))
            db.commit()
            db.close()
            context.user_data.clear()
            await update.message.reply_text(f"✅ تم تحديث الوقت بين الانضمامات إلى {d_val} ثانية.")
        except:
            db.close()
            await update.message.reply_text("⚠️ يرجى إرسال رقم صحيح بالثواني.")
        return

    if text == "💤 استراحة كل 5 روابط":
        db.close()
        context.user_data['action'] = 'set_rest'
        await update.message.reply_text("💤 أرسل عدد دقائق الاستراحة بعد كل 5 روابط (مثال: `5`):")
        return

    if action == 'set_rest':
        try:
            r_val = int(text)
            cursor.execute("UPDATE users SET rest_time=? WHERE user_id=?", (r_val, user_id))
            db.commit()
            db.close()
            context.user_data.clear()
            await update.message.reply_text(f"✅ تم تحديث وقت الاستراحة إلى {r_val} دقائق.")
        except:
            db.close()
            await update.message.reply_text("⚠️ يرجى إرسال رقم صحيح بالدقائق.")
        return

    if text == "🛑 إيقاف الانضمام":
        running_states[user_id] = False
        db.close()
        await update.message.reply_text("🛑 تم إيقاف عملية الانضمام بنجاح.")
        return

    if user_id == ADMIN_ID:
        if text == "👑 لوحة المطور":
            cursor.execute("SELECT COUNT(*) FROM users")
            u_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM accounts")
            a_count = cursor.fetchone()[0]
            db.close()
            await update.message.reply_text(
                f"👑 **لوحة تحكم المشرف العام:**\n\n"
                f"👥 إجمالي المستخدمين: {u_count}\n"
                f"📱 إجمالي الحسابات المسجلة: {a_count}",
                parse_mode="Markdown"
            )
            return

        if text == "🔋 شحن نقاط لمعلم":
            db.close()
            context.user_data['action'] = 'admin_add_points'
            await update.message.reply_text("🔋 أرسل آيدي المستخدم وعدد النقاط بهذه الفراغات:\n`USER_ID POINTS`\n(مثال: `123456789 50`)", parse_mode="Markdown")
            return

        if action == 'admin_add_points':
            try:
                parts = text.split()
                target_uid = int(parts[0])
                points = int(parts[1])
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (points, target_uid))
                db.commit()
                db.close()
                context.user_data.clear()
                await update.message.reply_text(f"✅ تم شحن {points} نقطة للمستخدم `{target_uid}` بنجاح.", parse_mode="Markdown")
            except Exception as e:
                db.close()
                await update.message.reply_text(f"❌ خطأ بالصيغة: {e}")
            return

        if text == "📢 إذاعة رسالة عامة":
            db.close()
            context.user_data['action'] = 'broadcast'
            await update.message.reply_text("📢 أرسل النص أو الرسالة التي تريد إذاعتها لجميع المستخدمين:")
            return

        if action == 'broadcast':
            cursor.execute("SELECT user_id FROM users")
            all_users = cursor.fetchall()
            db.close()
            context.user_data.clear()
            
            sent_count = 0
            for (u_id,) in all_users:
                try:
                    await context.bot.send_message(chat_id=u_id, text=f"📢 **إعلان إداري:**\n\n{text}", parse_mode="Markdown")
                    sent_count += 1
                except:
                    pass
            await update.message.reply_text(f"✅ تم إرسال الإذاعة بنجاح إلى ({sent_count}) مستخدم.")
            return

    if text == "🚀 بدء الانضمام":
        cursor.execute("SELECT id, link FROM links WHERE user_id=? AND status='pending'", (user_id,))
        links = cursor.fetchall()
        if not links: 
            db.close()
            return await update.message.reply_text("⚠️ لا توجد روابط في الانتظار.")
            
        cursor.execute("SELECT session, phone FROM accounts WHERE user_id=? AND is_active=1", (user_id,))
        active_acc = cursor.fetchone()
        if not active_acc:
            db.close()
            return await update.message.reply_text("❌ يرجى تفعيل حساب أو رقم أولاً.")
            
        cursor.execute("SELECT delay, rest_time FROM users WHERE user_id=?", (user_id,))
        user_conf = cursor.fetchone()
        db.close()
        
        running_states[user_id] = True
        asyncio.create_task(background_task(user_id, context, active_acc, user_conf[0], user_conf[1], links))
        return

    db.close()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data.startswith("del_acc_"):
        acc_id = int(data.split("_")[2])
        db = get_connection()
        cursor = db.cursor()
        cursor.execute("DELETE FROM accounts WHERE id=? AND user_id=?", (acc_id, user_id))
        db.commit()
        db.close()
        await query.edit_message_text("🗑️ تم حذف الرقم بنجاح.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).job_queue(None).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🚀 تم تشغيل البوت الاحترافي بنجاح...")
    app.run_polling()
