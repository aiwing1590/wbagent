from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import pandas as pd
import io
import os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Вставь свой ключ сюда (но лучше в переменные окружения Render)
client = OpenAI(api_key="ТВОЙ_OPENAI_API_KEY")

@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...), app_password: str = Form(...), user_query: str = Form(None)):
    if app_password != "Wb123prof":
        return {"error": "Неверный пароль!"}

    try:
        df = pd.read_excel(io.BytesIO(await file.read()))
        # Кратко превращаем таблицу в текст для ИИ
        stats_text = df.describe().to_string()
        
        # Если есть вопрос, отправляем его в GPT
        if user_query:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"Ты финансовый аналитик. Данные отчета: {stats_text[:1000]}"},
                    {"role": "user", "content": user_query}
                ]
            )
            return {"ai_response": response.choices[0].message.content}
        
        return {"status": "Файл загружен, задай вопрос ИИ."}
    except Exception as e:
        return {"error": str(e)}
