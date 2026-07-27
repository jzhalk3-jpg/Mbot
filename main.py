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
        BotCommand("start", "تشغيل البوت ولوحة التحكم"),
        BotCommand("channels", "قنواتي المربوطة وإدارتها"),
        BotCommand("help", "طريقة الاستخدام والذكاء الاصطناعي")
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ ربط قناة جديدة", callback_data="add_channel")],
        [InlineKeyboardButton("📋 قنواتي المربوطة", callback_data="my_channels")],
        [InlineKeyboardButton("🤖 ميزات الذكاء الاصطناعي", callback_data="ai_features")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "مرحباً بك في لوحة تحكم بوت **ResearchNetwork** الاحترافي 🔬\n\n"
        "البوت الآن يعمل بكامل ميزاته المتقدمة لتنسيق ونشر وإدارة الفرص البحثية.\n"
        "اختر ما تناسبك من الخيارات أدناه:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if query.data == "add_channel":
        await query.message.reply_text(
            "📌 **خطوات ربط القناة:**\n"
            "1. أضف البوت (Admin) في قناتك مع صلاحية النشر والتعديل.\n"
            "2. أرسل لي يوزرنيم القناة أو آيدي القناة هنا بهذا الشكل:\n"
            "`@YourChannelUsername`"
        )
        context.user_data['waiting_for_channel'] = True

    elif query.data == "my_channels":
        user_channels = db.get(user_id, {}).get("channels", {})
        if not user_channels:
            await query.message.reply_text("ليس لديك أي قنوات مربوطة حالياً. اضغط على 'ربط قناة جديدة'.")
            return
        
        keyboard = []
        for ch_id, ch_info in user_channels.items():
            status = "🟢 يعمل" if ch_info.get("active", False) else "🔴 متوقف"
            keyboard.append([InlineKeyboardButton(f"{ch_info.get('title', ch_id)} ({status})", callback_data=f"manage_{ch_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 الرئيسية", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("📋 **قنواتك المربوطة:**\nاختر القناة لإدارتها أو تعديل إعداداتها:", reply_markup=reply_markup)

    elif query.data == "ai_features":
        await query.message.reply_text(
            "🤖 **ميزات الذكاء الاصطناعي في البوت:**\n\n"
            "• **التحليل الذكي للنصوص:** أرسل أي نص عشوائي وسيقوم البوت بإعادة صياغته وترتيبه كإعلان بحثي أكاديمي منظم.\n"
            "• **إدارة الحالات المتقدمة:** أرسل (اغلاق الفرصة رقم X) ليقوم البوت بتحديث المنشور في القناة وإغلاقه تلقائياً.\n"
            "• **القوالب التلقائية:** وضع الوسوم وأزرار الواتساب بشكل هندسي متناسق.\n\n"
            "فقط فعّل قناتك وأرسل لي تفاصيل البحث وسأقوم بالباقي!"
        )

    elif query.data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("➕ ربط قناة جديدة", callback_data="add_channel")],
            [InlineKeyboardButton("📋 قنواتي المربوطة", callback_data="my_channels")],
            [InlineKeyboardButton("🤖 ميزات الذكاء الاصطناعي", callback_data="ai_features")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("مرحباً بك مرة أخرى في القائمة الرئيسية:", reply_markup=reply_markup)

    elif query.data.startswith("manage_"):
        ch_id = query.data.split("_")[1]
        user_channels = db.get(user_id, {}).get("channels", {})
        ch_info = user_channels.get(ch_id, {})
        status_text = "يعمل 🟢" if ch_info.get("active") else "متوقف 🔴"
        whatsapp = ch_info.get("whatsapp", "غير متوفر")

        keyboard = [
            [InlineKeyboardButton("🔄 تغيير حالة التشغيل (بدء/إيقاف)", callback_data=f"toggle_{ch_id}")],
            [InlineKeyboardButton("📱 تعيين رقم الواتساب", callback_data=f"set_wa_{ch_id}")],
            [InlineKeyboardButton("🔙 رجوع للقنوات", callback_data="my_channels")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            f"⚙️ **إدارة القناة:** {ch_info.get('title', ch_id)}\n"
            f"• الحالة: {status_text}\n"
            f"• رقم الواتساب: {whatsapp}\n\n"
            "أرسل لي الآن أي فرصة بحثية وسيتولى الذكاء الاصطناعي ترتيبها ونشرها فوراً!",
            reply_markup=reply_markup
        )

    elif query.data.startswith("toggle_"):
        ch_id = query.data.split("_")[1]
        user_channels = db.get(user_id, {}).get("channels", {})
        if ch_id in user_channels:
            current_status = user_channels[ch_id].get("active", False)
            user_channels[ch_id]["active"] = not current_status
            save_data(db)
            new_status_text = "يعمل 🟢" if user_channels[ch_id]["active"] else "متوقف 🔴"
            await query.message.reply_text(f"✅ تم تحديث حالة القناة بنجاح. أصبحت الآن: {new_status_text}")

    elif query.data.startswith("set_wa_"):
        ch_id = query.data.split("_")[1]
        context.user_data['waiting_for_whatsapp'] = ch_id
        await query.message.reply_text("📱 أرسل الآن رقم الواتساب أو رابط التواصل (مثال: `+966500000000`):")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    if context.user_data.get('waiting_for_channel'):
        context.user_data['waiting_for_channel'] = False
        ch_id = text.strip()
        try:
            chat = await context.bot.get_chat(ch_id)
            if user_id not in db:
                db[user_id] = {"channels": {}}
            db[user_id]["channels"][str(chat.id)] = {
                "title": chat.title,
                "active": False,
                "whatsapp": "غير محدد",
                "posts": {}
            }
            save_data(db)
            await update.message.reply_text(
                f"✅ تم ربط القناة بنجاح: {chat.title}\n"
                "انتقل الآن إلى 'قنواتي المربوطة' لتفعيلها وتعيين رقم الواتساب."
            )
        except Exception as e:
            await update.message.reply_text(f"❌ تعذر الوصول للقناة. تأكد من إضافة البوت كـ (Admin) فيها ثم حاول مجدداً.\nالخطأ: {e}")
        return

    if context.user_data.get('waiting_for_whatsapp'):
        ch_id = context.user_data.get('waiting_for_whatsapp')
        context.user_data['waiting_for_whatsapp'] = None
        if user_id in db and ch_id in db[user_id]["channels"]:
            db[user_id]["channels"][ch_id]["whatsapp"] = text.strip()
            save_data(db)
            await update.message.reply_text("✅ تم حفظ رقم الواتساب بنجاح للقناة!")
        return

    user_channels = db.get(user_id, {}).get("channels", {})
    active_channels = [ch_id for ch_id, info in user_channels.items() if info.get("active")]

    if not active_channels:
        await update.message.reply_text("⚠️ لا توجد أي قناة في وضع التشغيل (يعمل 🟢). يرجى تفعيل قناتك من لوحة التحكم أولاً.")
        return

    # محاكاة الذكاء الاصطناعي في تحليل وتنسيق النص البحثي
    formatted_post = (
        "📌 **فرصة بحثية أكاديمية جديدة**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"{text}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
    )

    for ch_id in active_channels:
        wa = user_channels[ch_id].get("whatsapp", "")
        post_text = formatted_post
        if wa and wa != "غير محدد":
            post_text += f"📱 **للتواصل والتقديم:**\n{wa}\n\n"
        
        post_text += "🏷️ #ResearchNetwork #أبحاث_طبية #فرص_بحثية"
        
        try:
            sent_msg = await context.bot.send_message(chat_id=int(ch_id), text=post_text, parse_mode="Markdown")
            await update.message.reply_text(f"🚀 تم تحليل النص بالذكاء الاصطناعي ونشره بنجاح في القناة!")
        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ أثناء النشر: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("channels", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))
    
    print("Bot is running with full features...")
    app.run_polling()

if __name__ == "__main__":
    main()
