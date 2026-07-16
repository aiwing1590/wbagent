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

SECRET_PASSWORD = "Wb123prof"

@app.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    app_password: str = Form(...),
    user_query: str = Form(None)
):
    if app_password != SECRET_PASSWORD:
        return {"error": "Неверный пароль от бэкенда!"}
    
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Безопасное чтение: если колонки нет, ставим 0.0
        rev = float(df['Валовая выручка'].sum()) if 'Валовая выручка' in df.columns else 0.0
        comm = float(df['Комиссия, эквайринг'].abs().sum()) if 'Комиссия, эквайринг' in df.columns else 0.0
        log = float(df['Логистика'].abs().sum()) if 'Логистика' in df.columns else 0.0
        cost = float(df['Себестоимость'].abs().sum()) if 'Себестоимость' in df.columns else 0.0
        
        total_costs = comm + log + cost
        profit = rev - total_costs
        
        # В словарь добавляем только те расходы, которые реально были найдены и посчитаны
        expenses_dict = {}
        if 'Логистика' in df.columns: expenses_dict["Логистика"] = log
        if 'Комиссия, эквайринг' in df.columns: expenses_dict["Комиссия"] = comm
        if 'Себестоимость' in df.columns: expenses_dict["Себестоимость"] = cost
        
        ai_ans = "Отчет успешно обработан. Задайте вопрос по данным."
        if user_query:
            q = user_query.lower()
            if "прибыл" in q or "аудит" in q:
                ai_ans = f"Чистая прибыль по данному отчету составляет {profit:,.2f} ₽. Общая выручка: {rev:,.2f} ₽."
            elif "расход" in q or "логистик" in q or "себестоимост" in q:
                ai_ans = f"Общая сумма расходов: {total_costs:,.2f} ₽. На логистику ушло {log:,.2f} ₽, а на закупку товара {cost:,.2f} ₽."
            elif "шутк" in q:
                ai_ans = "Почему программисты не любят природу? Потому что там слишком много багов!"
            else:
                ai_ans = f"Данные прочитаны. Выручка составляет {rev:,.0f} ₽. Уточните ваш вопрос (например, спросите про прибыль или логистику)."

        return {
            "total_revenue": rev,
            "net_profit": profit,
            "expenses": expenses_dict,
            "ai_response": ai_ans
        }
        
    except Exception as e:
        return {"error": f"Ошибка при чтении таблицы: {str(e)}"}
