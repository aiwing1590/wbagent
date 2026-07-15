from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_PASSWORD = "123"

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

ru_labels = {
    'Logistics': 'Логистика', 'Commission': 'Комиссия', 'Cost': 'Себестоимость',
    'Promo': 'Продвижение', 'Storage': 'Хранение', 'Acceptance': 'Приемка', 'Fines': 'Штрафы'
}

def detect_column(df, key):
    for col in df.columns:
        if any(syn in str(col).lower().strip() for syn in keywords_map[key]): return col
    return None

@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...), app_password: str = Form(...), user_query: str = Form(None)):
    if app_password != SECRET_PASSWORD: return {"error": "Неверный пароль"}
    try:
        df = pd.read_excel(io.BytesIO(await file.read()))
        found_cols = {k: detect_column(df, k) for k in keywords_map}
        
        rev_val = float(df[found_cols['revenue']].sum()) if found_cols['revenue'] else 0.0
        expenses_data = {}
        total_exp = 0.0
        for k in ['logistics', 'commission', 'cost', 'promo', 'storage', 'acceptance', 'fines']:
            col = found_cols[k]
            label = ru_labels[k.capitalize()]
            val = float(df[col].fillna(0).abs().sum()) if col else 0.0
            expenses_data[label] = val
            total_exp += val
        
        net_profit = rev_val - total_exp
        
        # Ответ ИИ (логика)
        ai_resp = "Анализ завершен. Используйте кнопки выше для получения детальных советов или поиска по товарам."
        if user_query:
            if "топ" in user_query.lower(): ai_resp = "Для детального анализа топов по товарам, пожалуйста, убедитесь, что в таблице есть колонка с наименованием."
            elif "аудит" in user_query.lower(): ai_resp = f"Финансовый аудит: Выручка {rev_val:,.0f}₽, Чистая прибыль {net_profit:,.0f}₽. Маржинальность составила {(net_profit/rev_val*100 if rev_val>0 else 0):.2f}%."
            else: ai_resp = "Я проанализировал ваш отчет. Задайте конкретный вопрос по расходам или товарам."

        return {"total_revenue": rev_val, "net_profit": net_profit, "expenses": expenses_data, "best_product": "Анализ завершен", "ai_response": ai_resp}
    except Exception as e: return {"error": str(e)}
