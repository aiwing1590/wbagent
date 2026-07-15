from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

keywords_map = {
    'revenue': ['валовая выручка', 'выручка по заказам', 'выручка', 'сумма'],
    'logistics': ['логистика', 'доставка'], 'commission': ['комиссия', 'эквайринг'],
    'cost': ['себестоимость'], 'promo': ['продвижение', 'реклама'],
    'storage': ['хранение'], 'acceptance': ['приемка'], 'fines': ['штрафы']
}
ru_labels = {'Logistics': 'Логистика', 'Commission': 'Комиссия', 'Cost': 'Себестоимость', 'Promo': 'Продвижение', 'Storage': 'Хранение', 'Acceptance': 'Приемка', 'Fines': 'Штрафы'}

@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...), app_password: str = Form(...), user_query: str = Form(None)):
    if app_password != "123": return {"error": "Неверный пароль"}
    try:
        df = pd.read_excel(io.BytesIO(await file.read()))
        # Находим колонку выручки
        rev_col = next((c for c in df.columns if any(k in str(c).lower() for k in keywords_map['revenue'])), df.columns[0])
        rev_val = float(df[rev_col].sum())
        
        expenses = {}
        total_exp = 0.0
        for k, labels in keywords_map.items():
            if k == 'revenue' or k == 'product_name' or k == 'date': continue
            col = next((c for c in df.columns if any(lab in str(c).lower() for lab in labels)), None)
            val = float(df[col].fillna(0).abs().sum()) if col else 0.0
            expenses[ru_labels.get(k.capitalize(), k.capitalize())] = val
            total_exp += val
            
        net_profit = rev_val - total_exp
        
        ai_ans = "Анализ завершен. Задайте вопрос по отчету."
        if user_query and "аудит" in user_query.lower():
            ai_ans = f"📊 Финансовый аудит:\nВыручка: {rev_val:,.0f} ₽.\nЧистая прибыль: {net_profit:,.0f} ₽.\nРентабельность: {(net_profit/rev_val*100 if rev_val>0 else 0):.1f}%."
        
        return {"total_revenue": rev_val, "net_profit": net_profit, "expenses": expenses, "ai_response": ai_ans}
    except Exception as e: return {"error": str(e)}
