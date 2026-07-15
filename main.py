from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SECRET_PASSWORD = "Wb123prof"

@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...), app_password: str = Form(...), user_query: str = Form(None)):
    if app_password != SECRET_PASSWORD:
        return {"error": "Неверный пароль!"}
    
    try:
        df = pd.read_excel(io.BytesIO(await file.read()))
        
        # Считаем корректно:
        rev = df['Валовая выручка'].sum()
        # Берем модули (abs), так как в таблице себестоимость записана отрицательными числами
        comm = df['Комиссия, эквайринг'].abs().sum()
        log = df['Логистика'].abs().sum()
        cost = df['Себестоимость'].abs().sum()
        
        profit = rev - (comm + log + cost)
        
        expenses = {
            "Логистика": log,
            "Комиссия": comm,
            "Себестоимость": cost
        }

        if user_query:
            return {"ai_response": f"Прибыль составляет {profit:,.2f} ₽. Выручка: {rev:,.2f} ₽."}

        return {
            "total_revenue": rev,
            "net_profit": profit,
            "expenses": expenses
        }
    except Exception as e:
        return {"error": str(e)}
