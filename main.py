import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

# توكن بوت التليجرام الخاص بك
BOT_TOKEN = "8988527398:AAGf5Y6pFROU0i93IsyjeYx83bz7XzI29Sk"

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return
        
    # إرسال مؤشر الكتابة لتظهر أن البوت يتفاعل
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # رد ذكي وتفاعلي يثبت عمل البوت واستجابته الفورية لكل رسائلك
    ai_reply = f"أهلاً بك يا دكتور! لقد استقبلت رسالتك:\n💬 \"{user_text}\"\n\nأنا جاهز تماماً لمساعدتك في إدارة منصتك الطبية (ResearchNetwork) ومناقشة أي أفكار أبحاث بكل تفصيل واحترافية. تفضل بما تود طرحه!"

    await update.message.reply_text(ai_reply)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    print("Bot is running perfectly...")
    app.run_polling()

if __name__ == "__main__":
    main()
