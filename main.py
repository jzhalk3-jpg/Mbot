import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import google.generativeai as genai

app = FastAPI()

# تفعيل مفتاح الذكاء الاصطناعي من سحابة المنصة
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "")
    
    if not user_message:
        return {"reply": "الرجاء كتابة رسالة."}

    try:
        # استخدام موديل جيميناي السريع للرد على كل زوار الموقع
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(user_message)
        
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "عذراً، حدث خطأ مؤقت في النظام. تأكد من صحة مفتاح الذكاء الاصطناعي في إعدادات المنصة."}
