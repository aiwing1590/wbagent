from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_PASSWORD = "123"

# Словарь синонимов
keywords_map = {
    'revenue': ['валовая выручка', 'выручка по заказам', 'выручка', 'сумма реализации', 'сумма заказов'],
    'logistics': ['логистика', 'доставка'],
    'commission': ['комиссия', 'эквайринг'],
    'cost': ['себестоимость'],
    'promo': ['продвижение', 'реклама'],
    'storage': ['хранение'],
    'acceptance': ['приемка', 'платная приемка'],
    'fines': ['штрафы', 'штраф'],
    'product_name': ['наименование', 'товар', 'артикул'],
    'date': ['дата', 'день']
}

# Словарь перевода для отображения на сайте
ru_labels = {
    'Logistics': 'Логистика',
    'Commission': 'Комиссия',
    'Cost': 'Себестоимость',
    'Promo': 'Продвижение',
    'Storage': 'Хранение',
    'Acceptance': 'Приемка',
    'Fines': 'Штрафы'
}

def detect_column(df, key):
    for col in df.columns:
        col_lower = str(col).lower().strip()
        if any(syn in col_lower for syn in keywords_map[key]):
            return col
    return None

@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...), app_password: str = Form(...), user_query: str = Form(None)):
    if app_password != SECRET_PASSWORD:
        return {"error": "Неверный пароль"}
    
    try:
        df = pd.read_excel(io.BytesIO(await file.read()))
        found_cols = {k: detect_column(df, k) for k in keywords_map}
        
        rev_val = float(df[found_cols['revenue']].sum()) if found_cols['revenue'] else 0.0
        
        expenses_data = {}
        total_exp = 0.0
        # Проходим по ключам и сразу используем русский перевод
        for k in ['logistics', 'commission', 'cost', 'promo', 'storage', 'acceptance', 'fines']:
            col = found_cols[k]
            label = ru_labels[k.capitalize()] # Берем перевод
            if col:
                val = float(df[col].fillna(0).abs().sum())
                expenses_data[label] = val
                total_exp += val
            else:
                expenses_data[label] = 0.0
        
        net_profit = rev_val - total_exp

        return {
            "total_revenue": rev_val,
            "net_profit": net_profit,
            "expenses": expenses_data,
            "best_product": "Анализ завершен успешно",
            "ai_response": "Все данные успешно проанализированы."
        }
    except Exception as e:
        return {"error": str(e)}
