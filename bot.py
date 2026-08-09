from dotenv import load_dotenv
import os
import logging
import openai
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Try to import transformers for a free local fallback (runs on your server, may be slow)
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

# Load environment variables from .env if present
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# Optional Telegram API ID / HASH if you later use Telethon
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set. Please set the environment variable or use a .env file based on .env.example")

# If an OpenAI key is provided we will use it. Otherwise we will try to use a local transformers model as a free fallback.
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prepare a transformers generator lazily if needed
_transformer_generator = None
async def _get_transformer_generator():
    global _transformer_generator
    if _transformer_generator is None:
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("Transformers is not installed. Install transformers and torch to use the free local fallback.")
        # This can download the model the first time and may take time and disk space.
        # We use the small 'gpt2' model for CPU-friendly usage. For better results, use a bigger model (requires more RAM).
        _transformer_generator = pipeline('text-generation', model='gpt2')
    return _transformer_generator

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً! أنا بوت ذكي. أرسل لي رسالة وسأجيب باستخدام OpenAI إذا كان متوفراً، وإلا سأستخدم مولد محلي مجاني (قد يكون أبطأ).")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ببساطة اكتب سؤالك أو رسالتك، وسأرد عليك.")

async def _generate_with_openai(user_text: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_text}],
            max_tokens=600,
            temperature=0.6,
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.exception("OpenAI request failed")
        return "حصل خطأ أثناء الوصول إلى OpenAI: " + str(e)

async def _generate_with_transformers(user_text: str) -> str:
    try:
        generator = await _get_transformer_generator()
        # transformers pipeline is synchronous and blocking — run in a thread
        def _call():
            # num_return_sequences=1, max_length controls generation length
            out = generator(user_text, max_length=150, num_return_sequences=1)
            return out
        out = await asyncio.to_thread(_call)
        text = out[0]['generated_text']
        # The generator returns the prompt plus continuation; remove the original prompt prefix if present
        if text.startswith(user_text):
            return text[len(user_text):].strip()
        return text.strip()
    except Exception as e:
        logger.exception("Local transformer generation failed")
        return "حصل خطأ أثناء التوليد المحلي: " + str(e)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    logger.info(f"Received message from {chat_id}: {user_text}")

    # Choose backend: OpenAI if key present, otherwise transformers fallback
    if OPENAI_API_KEY:
        reply = await _generate_with_openai(user_text)
    else:
        try:
            reply = await _generate_with_transformers(user_text)
        except Exception as e:
            reply = ("لم يتوفر مفتاح OpenAI ولا مكتبة transformers محلية. لتشغيل بدون رسوم،
                    "
                    "ثبّت المكتبتين (transformers و torch) على الخادم أو زوّدني بمفتاح OpenAI).\n\nError: " + str(e))

    await update.message.reply_text(reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Starting bot...")
    app.run_polling()
