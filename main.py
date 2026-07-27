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

# تم تثبيت الآيدي الخاص بك كمدير للبوت
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
        BotCommand("start", "لوحة التحكم الرئيسية للبوت")
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in db:
        db[user_id] = {"publishing": True, "channels": {}}
        save_data(db)
        
    is_publishing = db[user_id].get("publishing", True)
    pub_status = "🟢 النشر مفعل" if is_publishing else "🔴 النشر متوقف"

    keyboard = [
        [InlineKeyboardButton("➕ ربط قناة جديدة", callback_data="add_channel")],
        [InlineKeyboardButton("📋 قنواتي المربوطة", callback_data="my_channels")],
        [InlineKeyboardButton("🚀 بدء النشر", callback_data="start_publishing"), InlineKeyboardButton("⏹ إيقاف النشر", callback_data="stop_publishing")],
        [InlineKeyboardButton("🤖 اقتراحات الذكاء الاصطناعي للأبحاث", callback_data="ai_suggestions")],
        [InlineKeyboardButton("⏰ جدول المنشورات", callback_data="schedule_menu")]
    ]

    # إذا كان المستخدم هو أنت (الآيدي الخاص بك)، يظهر له زر إضافي للتحكم العام بالبوت
    if user_id == ADMIN_ID:
        global_active = db.get("global_system_active", True)
        global_status_btn = "🔴 إيقاف البوت عن الجميع (صلاحية مدير)" if global_active else "🟢 تشغيل البوت للجميع (صلاحية مدير)"
        keyboard.append([InlineKeyboardButton(global_status_btn, callback_data="toggle_global_system")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🔬 **لوحة تحكم ResearchNetwork الذكية**\n\n"
        f"حالة النشر الخاصة بك: {pub_status}\n\n"
        "أرسل لي نص الإعلان أو تفاصيل الفرصة البحثية (مع أي روابط أو طرق تواصل تريدها)، وسيقوم الذكاء الاصطناعي بصياغتها ونشرها فوراً بالقالب الاحترافي!"
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
        current_global = db.get("global_system_active", True)
        db["global_system_active"] = not current_global
        save_data(db)
        await query.answer("⚙️ تم تغيير حالة النظام العامة بنجاح!", show_alert=True)
        await start(update, context)

    elif query.data == "start_publishing":
        if user_id not in db:
            db[user_id] = {}
        db[user_id]["publishing"] = True
        save_data(db)
        await query.answer("✅ تم تفعيل النشر بنجاح!", show_alert=True)
        await start(update, context)

    elif query.data == "stop_publishing":
        if user_id not in db:
            db[user_id] = {}
        db[user_id]["publishing"] = False
        save_data(db)
        await query.answer("⏹ تم إيقاف النشر مؤقتاً.", show_alert=True)
        await start(update, context)

    elif query.data == "add_channel":
        await query.message.edit_text(
            "📌 **خطوات ربط القناة:**\n"
            "1. أضف البوت (Admin) في قناتك مع صلاحية النشر.\n"
            "2. أرسل لي يوزرنيم القناة هنا (مثال: `@YourChannel`):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
        )
        context.user_data['waiting_for_channel'] = True

    elif query.data == "my_channels":
        user_channels = db.get(user_id, {}).get("channels", {})
        if not user_channels:
            await query.message.edit_text(
                "ليس لديك أي قنوات مربوطة حالياً.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
            )
            return
        
        keyboard = []
        for ch_id, ch_title in user_channels.items():
            keyboard.append([InlineKeyboardButton(f"📢 {ch_title} (حذف)", callback_data=f"del_ch_{ch_id}")])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
        
        await query.message.edit_text("📋 **قنواتك المربوطة حالياً:**\n(اضغط على القناة لإلغاء ربطها)", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("del_ch_"):
        ch_id = query.data.split("_")[2]
        if ch_id in db[user_id]["channels"]:
            del db[user_id]["channels"][ch_id]
            save_data(db)
        await query.message.edit_text("✅ تم إلغاء ربط القناة بنجاح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))

    elif query.data == "ai_suggestions":
        ai_text = (
            "🤖 **مقترحات الذكاء الاصطناعي الجاهزة:**\n\n"
            "• **تخصص:** جراحة المخ والأعصاب (Neurosurgery)\n"
            "• **التصنيف:** Q1 / PubMed / Scopus\n\n"
            "💡 *طريقة الاستخدام:* أرسل تفاصيل التخصص مع أي روابط تواصل تفضلها، وسيقوم البوت بتنسيقها ونشرها فوراً بالشكل المطلوب!"
        )
        await query.message.edit_text(ai_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))

    elif query.data == "schedule_menu":
        await query.message.edit_text(
            "⏰ **قسم جدول المنشورات:**\n\n"
            "ميزة الجدولة الزمنية للمنشورات قيد التفعيل التلقائي.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]))

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    # التحقق مما إذا كان النظام موقوفاً عاماً من قبل المدير (أنت)
    if not db.get("global_system_active", True) and user_id != ADMIN_ID:
        await update.message.reply_text("🔴 عذراً، البوت متوقف مؤقتاً من قبل الإدارة.")
        return

    if user_id not in db:
        db[user_id] = {"publishing": True, "channels": {}}

    if not db[user_id].get("publishing", True):
        await update.message.reply_text("⏹ النشر متوقف حالياً لديك. اضغط على زر (بدء النشر) من لوحة التحكم /start لتمكينه.")
        return

    if context.user_data.get('waiting_for_channel'):
        context.user_data['waiting_for_channel'] = False
        ch_id = text.strip()
        try:
            chat = await context.bot.get_chat(ch_id)
            db[user_id]["channels"][str(chat.id)] = chat.title
            save_data(db)
            await update.message.reply_text(f"✅ تم ربط القناة بنجاح: {chat.title}\nيمكنك الآن إرسال أي نص بحثي ليقوم البوت بنشره.")
        except Exception as e:
            await update.message.reply_text(f"❌ تعذر الوصول للقناة. تأكد من إضافة البوت مشرفاً (Admin) فيها.\nالخطأ: {e}")
        return

    user_channels = db[user_id].get("channels", {})
    if not user_channels:
        await update.message.reply_text("⚠️ لم تقم بربط أي قناة بعد! أرسل /start لربط قناتك أولاً.")
        return

    # الذكاء الاصطناعي يدمج النص والروابط وطرق التواصل التي ترسلها تماماً بحرية واحترافية
    smart_post = (
        "يسر منصة #ResearchNetwork الإعلان عن فرصة بحثية للمشاركة:\n\n"
        f"{text}\n\n"
        "🌍 تصنيف النشر المستهدف:\n"
        "مجلات علمية عالمية مرموقة (Q1 / Q2) ومفهرسة في:\n"
        "PubMed | Scopus | Web of Science\n\n"
        "✅ المميزات:\n"
        "🔹 متوافقة تماماً مع معايير ومتطلبات الهيئات الصحية.\n"
        "🔹 تدعم مسارات التقديم على برامج البورد، الزمالات الدقيقة، الابتعاث، والترقيات.\n\n"
        "🌐 قناتنا الرسمية:\n"
        "https://t.me/Research_Network"
    )

    for ch_id in user_channels.keys():
        try:
            await context.bot.send_message(chat_id=int(ch_id), text=smart_post)
            await update.message.reply_text("🚀 تم معالجة النص وصياغته ونشره بنجاح في قناتك!")
        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ أثناء النشر في القناة: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))
    
    print("Bot is running with persistent admin config...")
    app.run_polling()

if __name__ == "__main__":
    main()
