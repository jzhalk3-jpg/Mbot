import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8988527398:AAGf5Y6pFROU0i93IsyjeYx83bz7XzI29Sk"

# المفتاح الذي أرسلته والمعتمد في حسابك
GEMINI_API_KEY = "AQ.Ab8RN6KCY0D9T2kzBElJSI9zyl5Jk_MYzQpbcxaJEEL3QOdoIg"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    try:
        response = model.generate_content(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"خطأ تقني في الاتصال:\n{str(e)}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    print("AI Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
