import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import google.generativeai as genai

app = FastAPI()

# جلب مفتاح الذكاء الاصطناعي وتشغيله
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
    
    # استخدام أحدث نموذج ذكاء اصطناعي من جوجل للرد الفوري
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(user_message)
    
    return {"reply": response.text}
