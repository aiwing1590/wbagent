from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

app = FastAPI()

# Настройки CORS (чтобы Vercel мог общаться с Render)
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
    # Жесткая проверка пароля
    if app_password != SECRET_PASSWORD:
        return {"error": "Неверный пароль от бэкенда!"}
    
    try:
        # Чтение файла
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Подсчет Выручки
        rev = float(df['Валовая выручка'].sum())
        
        # Подсчет расходов (берем по модулю .abs(), чтобы не было проблем с минусами)
        comm = float(df['Комиссия, эквайринг'].abs().sum())
        log = float(df['Логистика'].abs().sum())
        cost = float(df['Себестоимость'].abs().sum())
        
        total_costs = comm + log + cost
        profit = rev - total_costs
        
        expenses_dict = {
            "Логистика": log,
            "Комиссия": comm,
            "Себестоимость": cost
        }
        
        # Логика ответов ИИ
        ai_ans = "Отчет успешно обработан. Задайте вопрос по данным."
        if user_query:
            q = user_query.lower()
            if "прибыл" in q or "аудит" in q:
                ai_ans = f"Чистая прибыль по данному отчету составляет {profit:,.2f} ₽. Общая выручка: {rev:,.2f} ₽."
            elif "расход" in q or "логистик" in q or "себестоимост" in q:
                ai_ans = f"Общая сумма расходов: {total_costs:,.2f} ₽. На логистику ушло {log:,.2f} ₽, а на закупку товара (себестоимость) {cost:,.2f} ₽."
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
