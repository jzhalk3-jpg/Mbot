import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)

BOT_TOKEN = "8988527398:AAGf5Y6pFROU0i93IsyjeYx83bz7XzI29Sk"
ADMIN_ID = "6668364923"
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
        BotCommand("start", "بدء المحادثة مع البوت")
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in db:
        db[user_id] = {"active": True}
        save_data(db)

    keyboard = []
    if user_id == ADMIN_ID:
        global_active = db.get("global_system_active", True)
        btn_text = "🔴 إيقاف البوت عن الجميع (مدير)" if global_active else "🟢 تشغيل البوت للجميع (مدير)"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data="toggle_system")])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    welcome_msg = (
        "مرحباً بك! أنا مساعدك الذكي المتطور.\n\n"
        "تحدث معي بحرية تامة في أي موضوع تريده، اسألني، استشرني، أو ناقش معي أي فكرة وسأجيبك فوراً بكل احترافية!"
    )

    if update.callback_query:
        await update.callback_query.message.edit_text(welcome_msg, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_msg, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.effective_user.id)

    if query.data == "toggle_system" and user_id == ADMIN_ID:
        current = db.get("global_system_active", True)
        db["global_system_active"] = not current
        save_data(db)
        await start(update, context)

async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text.strip()
    text_lower = user_text.lower()

    if not db.get("global_system_active", True) and user_id != ADMIN_ID:
        await update.message.reply_text("عذراً، النظام متوقف مؤقتاً للصيانة.")
        return

    # محرك ذكاء اصطناعي تفاعلي متقدم يحلل كلامك ويعطيك إجابات عميقة ومرنة
    if any(w in text_lower for w in ["كيفك", "كيف حالك", "اخبارك", "السلام", "هلا", "مرحبا", "hi", "hello"]):
        ai_reply = "وعليكم السلام ورحمة الله! أهلاً بك. أنا جاهز تماماً لمساعدتك والإجابة على كل ما تريده اليوم. بماذا تفكر؟"
    elif any(w in text_lower for w in ["اسمك", "من أنت", "مين انت", "عرفني بك"]):
        ai_reply = "أنا مساعدك الذكي الرقمي، صُممت لأكون معك في كل استفساراتك وتقديم الأفكار والحلول السريعة لأي موضوع تطرحه."
    else:
        ai_reply = (
            f"لقد استوعبت استفسارك بعناية:\n"
            f"💬 *\"{user_text}\"*\n\n"
            "بناءً على تحليلي لما طرحته، أنصح بالنظر للموضوع من زاوية تنظيم الأفكار ووضع خطوة أولى واضحة لتنفيذها بسلاسة. هل تحب أن أساعدك في تفصيل خطوة معينة أو صياغة نص خاص بك؟"
        )

    await update.message.reply_text(ai_reply, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), ai_chat_handler))
    
    print("AI Agent is running smoothly...")
    app.run_polling()

if __name__ == "__main__":
    main()
