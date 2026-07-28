import json
import os
import google.generativeai as genai
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

# ضع مفتاحك الصحيح هنا مباشرة (الذي يبدأ بـ AIza...)
# يرجى نسخ المفتاح الكامل بالضغط على أيقونة النسخ بجوار المفتاح في صورتك ووضعه هنا بين الأقواس:
GEMINI_API_KEY = "نسخ_المفتاح_من_صورة_جوجل_وهنا_مكانة"

genai.configure(api_key=GEMINI_API_KEY)

# إعداد نموذج جيميني للرد بذكاء اصطناعي كامل
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="أنت مساعد ذكي ومنصة تسمى RESEARCHNETWORK متخصصة في الأبحاث الطبية، تنظيم الفرص الأكاديمية، ومساعدة الأطباء والباحثين. أجب بكل احترافية وتفاعل على كل رسالة."
)

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
        BotCommand("start", "بدء المحادثة مع RESEARCHNETWORK")
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
        "مرحباً بك يا دكتور! أنا **RESEARCHNETWORK**، مساعدك الذكي المتطور.\n\n"
        "تحدث معي بحرية تامة: اسألني عن الأبحاث الطبية، استشرني في صياغة الإعلانات، أو ناقش معي أي فكرة وسأجيبك بذكاء اصطناعي حقيقي فوراً!"
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
    user_text = update.message.text

    if not db.get("global_system_active", True) and user_id != ADMIN_ID:
        await update.message.reply_text("عذراً، نظام **RESEARCHNETWORK** متوقف مؤقتاً للصيانة من قبل الإدارة.")
        return

    try:
        # إرسال الرسالة إلى نموذج جيميني الحقيقي واستقبال الرد الذكي
        response = model.generate_content(user_text)
        ai_reply = response.text
    except Exception as e:
        ai_reply = f"عذراً يا دكتور، تأكد من وضع مفتاح API الصحيح في الكود. الخطأ التقني:\n`{str(e)}`"

    await update.message.reply_text(ai_reply, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), ai_chat_handler))
    
    print("RESEARCHNETWORK AI Agent is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
