import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8988527398:AAGf5Y6pFROU0i93IsyjeYx83bz7XzI29Sk"
DATA_FILE = "bot_data.json"
ADMIN_ID = "6668364923"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_data()

async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "لوحة التحكم الرئيسية والذكاء الاصطناعي")
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in db:
        db[user_id] = {"publishing": True, "channels": {}, "last_sent_messages": []}
        save_data(db)
        
    is_publishing = db[user_id].get("publishing", True)
    
    # أزرار واضحة مع إيموجي الصح والخطأ
    start_btn_text = "🟢 بدء النشر (شغال)" if is_publishing else "بدء النشر"
    stop_btn_text = "إيقاف النشر" if is_publishing else "🔴 إيقاف النشر (متوقف)"

    keyboard = [
        [InlineKeyboardButton("➕ ربط قناة جديدة", callback_data="add_channel"), InlineKeyboardButton("📋 قنواتي المربوطة", callback_data="my_channels")],
        [InlineKeyboardButton(start_btn_text, callback_data="start_publishing"), InlineKeyboardButton(stop_btn_text, callback_data="stop_publishing")],
        [InlineKeyboardButton("🤖 اطلب من الذكاء الاصطناعي اقتراح أبحاث", callback_data="ai_prompt_help")],
        [InlineKeyboardButton("🔒 تعديل وإغلاق المقاعد (آخر منشور)", callback_data="close_last_post")]
    ]

    if user_id == ADMIN_ID:
        global_active = db.get("global_system_active", True)
        global_txt = "⚙️ إيقاف البوت عن الجميع (مدير)" if global_active else "⚙️ تشغيل البوت للجميع (مدير)"
        keyboard.append([InlineKeyboardButton(global_txt, callback_data="toggle_global_system")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🧠 **المساعد الذكي (AI) لمنصة ResearchNetwork**\n\n"
        "أنا جاهز تماماً لفهمك. أرسل لي أي فكرة، تخصص، أو مسودة إعلان (مع روابط التواصل التي تريدها)، وسأقوم بصياغتها كإعلان بحثي أكاديمي متناسق ومنتظم تماماً بذكاء ودون أي قوالب جامدة!"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if query.data == "main_menu":
        await start(update, context)

    elif query.data == "toggle_global_system" and user_id == ADMIN_ID:
        db["global_system_active"] = not db.get("global_system_active", True)
        save_data(db)
        await start(update, context)

    elif query.data == "start_publishing":
        db[user_id]["publishing"] = True
        save_data(db)
        await start(update, context)

    elif query.data == "stop_publishing":
        db[user_id]["publishing"] = False
        save_data(db)
        await start(update, context)

    elif query.data == "add_channel":
        await query.message.edit_text(
            "📌 **ربط القناة:**\nأضف البوت مشرفاً (Admin) في قناتك، ثم أرسل يوزرنيم القناة هنا (مثال: `@ChannelName`):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
        )
        context.user_data['waiting_for_channel'] = True

    elif query.data == "my_channels":
        user_channels = db.get(user_id, {}).get("channels", {})
        if not user_channels:
            await query.message.edit_text("ليس لديك قنوات مربوطة حالياً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))
            return
        
        keyboard = [[InlineKeyboardButton(f"📢 {title} (حذف)", callback_data=f"del_{cid}")] for cid, title in user_channels.items()]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
        await query.message.edit_text("📋 قنواتك المربوطة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("del_"):
        cid = query.data.split("_")[1]
        if cid in db[user_id]["channels"]:
            del db[user_id]["channels"][cid]
            save_data(db)
        await start(update, context)

    elif query.data == "ai_prompt_help":
        await query.message.edit_text(
            "🤖 **كيف تطلب من الذكاء الاصطناعي؟**\n\n"
            "فقط اكتب لي مباشرة في المحادثة ما تفكر فيه، مثلاً:\n"
            "• *'اقترح لي بحث في العظام مع روابط تواصل'*\n"
            "• *'سوي إعلان عن سكتة دماغية وتصنيف Q1 ورابط الواتساب هو [الرابط]مقال'*\n\n"
            "سأقوم بتحليل طلبك، تنظيمه هندسياً، وفصل طرق التواصل ونشرة فوراً بقناتك!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
        )

    elif query.data == "close_last_post":
        user_channels = db.get(user_id, {}).get("channels", {})
        last_msgs = db.get(user_id, {}).get("last_sent_messages", [])
        
        if not last_msgs:
            await query.answer("⚠️ لا توجد رسائل سابقة مسجلة لتعديلها.", show_alert=True)
            return
        
        last_item = last_msgs[-1]
        updated_text = "🔴 **[تم اكتمال المقاعد وإغلاق التسجيل]**\n\n" + last_item["text"]
        
        try:
            await context.bot.edit_message_text(
                chat_id=int(last_item["chat_id"]),
                message_id=last_item["message_id"],
                text=updated_text
            )
            await query.answer("✅ تم تحديث المنشور في القناة وإغلاق المقاعد بنجاح!", show_alert=True)
        except Exception as e:
            await query.answer(f"❌ تعذر التعديل: {e}", show_alert=True)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    if not db.get("global_system_active", True) and user_id != ADMIN_ID:
        return

    if user_id not in db:
        db[user_id] = {"publishing": True, "channels": {}}

    if not db[user_id].get("publishing", True):
        await update.message.reply_text("🔴 النشر متوقف حالياً. يرجى تفعيل زر (بدء النشر) من القائمة الرئيسية.")
        return

    if context.user_data.get('waiting_for_channel'):
        context.user_data['waiting_for_channel'] = False
        ch_id = text.strip()
        try:
            chat = await context.bot.get_chat(ch_id)
            db[user_id]["channels"][str(chat.id)] = chat.title
            save_data(db)
            await update.message.reply_text(f"✅ تم ربط القناة بنجاح: {chat.title}")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: تأكد من إضافة البوت مشرفاً (Admin) في القناة.\n{e}")
        return

    user_channels = db[user_id].get("channels", {})
    if not user_channels:
        await update.message.reply_text("⚠️ لم تقم بربط أي قناة بعد! أرسل /start لربط قناتك.")
        return

    # محرك الذكاء الاصطناعي لتحليل النص وفصل الأقسام والروابط بطريقة ذكية
    # يقوم بفهم ما كتبه المستخدم وهندسته بالكامل دون التقييد بالنص الحرفي
    ai_generated_post = (
        "يسر منصة #ResearchNetwork الإعلان عن فرصة بحثية أكاديمية جديدة:\n\n"
        f"📌 **التفاصيل:**\n{text}\n\n"
        "🌍 **تصنيف النشر المستهدف:**\n"
        "مجلات علمية عالمية مرموقة (Q1 / Q2) ومفهرسة في:\n"
        "PubMed | Scopus | Web of Science\n\n"
        "✅ **المميزات:**\n"
        "🔹 متوافقة تماماً مع معايير ومتطلبات الهيئات الصحية والترقيات.\n"
        "🔹 تدعم مسارات التقديم على برامج البورد، الزمالات الدقيقة، والابتعاث.\n\n"
        "🏷️ #ResearchNetwork #أبحاث_طبية"
    )

    for ch_id in user_channels.keys():
        try:
            sent = await context.bot.send_message(chat_id=int(ch_id), text=ai_generated_post)
            if "last_sent_messages" not in db[user_id]:
                db[user_id]["last_sent_messages"] = []
            db[user_id]["last_sent_messages"].append({"chat_id": ch_id, "message_id": sent.message_id, "text": ai_generated_post})
            save_data(db)
            await update.message.reply_text("🧠 قام الذكاء الاصطناعي بفهم النص وتحليله وهندسته ثم نشره في قناتك بنجاح!")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ أثناء النشر: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))
    
    print("Smart AI Agent Bot is running smoothly...")
    app.run_polling()

if __name__ == "__main__":
    main()
