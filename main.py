from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/analyze")
async def analyze(file: UploadFile = File(...), app_password: str = Form(...)):
    if app_password != "Wb123prof": return {"error": "Пароль неверный"}
    try:
        df = pd.read_excel(io.BytesIO(await file.read()))
        rev = float(df['Валовая выручка'].sum())
        # Используем abs(), так как в таблице расходы отрицательные
        costs = df['Комиссия, эквайринг'].abs().sum() + df['Логистика'].abs().sum() + df['Себестоимость'].abs().sum()
        profit = rev - costs
        return {"total_revenue": round(rev, 2), "net_profit": round(profit, 2)}
    except Exception as e: return {"error": str(e)}
