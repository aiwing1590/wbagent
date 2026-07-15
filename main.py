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

# Пароль для доступа
SECRET_PASSWORD = "123"

# Словарь синонимов для поиска колонок
keywords_map = {
    'revenue': ['валовая выручка', 'выручка по заказам', 'выручка', 'сумма реализации', 'сумма'],
    'logistics': ['логистика', 'доставка'],
    'commission': ['комиссия', 'эквайринг'],
    'cost': ['себестоимость'],
    'promo': ['продвижение', 'реклама'],
    'storage': ['хранение'],
    'acceptance': ['приемка', 'платная приемка'],
    'fines': ['штрафы', 'штраф']
}

# Перевод для отображения в интерфейсе
ru_labels = {
    'Logistics': 'Логистика', 'Commission': 'Комиссия', 'Cost': 'Себестоимость',
    'Promo': 'Продвижение', 'Storage': 'Хранение', 'Acceptance': 'Приемка', 'Fines': 'Штрафы'
}

def detect_column(df, key):
    for col in df.columns:
        if any(syn in str(col).lower().strip() for syn in keywords_map[key]):
            return col
    return None

@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...), app_password: str = Form(...), user_query: str = Form(None)):
    # 1. Жесткая проверка пароля
    if app_password != SECRET_PASSWORD:
        return {"error": "Неверный пароль! Доступ запрещен."}
    
    # Если пришел пустой файл (проверка пароля на этапе логина)
    if not file.filename:
        return {"status": "ok"}

    try:
        df = pd.read_excel(io.BytesIO(await file.read()))
        found_cols = {k: detect_column(df, k) for k in keywords_map}
        
        # Считаем выручку
        rev_val = float(df[found_cols['revenue']].sum()) if found_cols['revenue'] else 0.0
        
        # Считаем расходы
        expenses_data = {}
        total_exp = 0.0
        for k in ['logistics', 'commission', 'cost', 'promo', 'storage', 'acceptance', 'fines']:
            col = found_cols[k]
            label = ru_labels[k.capitalize()]
            val = float(df[col].fillna(0).abs().sum()) if col else 0.0
            expenses_data[label] = val
            total_exp += val
        
        net_profit = rev_val - total_exp
        
        # Базовая логика ИИ-ответов
        ai_ans = "Отчет успешно обработан. Используйте кнопки выше для получения данных."
        if user_query:
            q = user_query.lower()
            if "аудит" in q:
                ai_ans = f"📊 Финансовый аудит:\nВыручка: {rev_val:,.0f} ₽\nЧистая прибыль: {net_profit:,.0f} ₽\nМаржинальность: {(net_profit/rev_val*100 if rev_val>0 else 0):.1f}%"
            elif "логистик" in q:
                log_val = expenses_data.get('Логистика', 0)
                ai_ans = f"🚚 Затраты на логистику составили {log_val:,.0f} ₽ ({(log_val/rev_val*100 if rev_val>0 else 0):.1f}% от выручки)."
        
        return {
            "total_revenue": rev_val,
            "net_profit": net_profit,
            "expenses": expenses_data,
            "ai_response": ai_ans
        }
    except Exception as e:
        return {"error": f"Ошибка анализа: {str(e)}"}
