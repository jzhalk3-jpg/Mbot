import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import google.generativeai as genai

app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

@app.get("/", response_class=HTMLResponse)
async def home():
    # قراءة ملف index.html مباشرة من مجلد templates بدون مشاكل توافقية
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return "<h1>مرحباً، جاري تجهيز الموقع...</h1>"

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "")
    
    try:
        response = model.generate_content(user_message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "عذراً، حدث خطأ في الاتصال بالذكاء الاصطناعي."}
