from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

app = FastAPI()

# 1. НАСТРОЙКА БЕЗОПАСНОСТИ (CORS)
# Разрешаем твоему сайту на Vercel общаться с этим сервером на Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === ТВОЙ ПАРОЛЬ ДЛЯ ВХОДА НА САЙТ ===
SECRET_PASSWORD = "123"

@app.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    app_password: str = Form(...),
    user_query: str = Form(None)
):
    # 2. ПРОВЕРКА ПАРОЛЯ
    if app_password != SECRET_PASSWORD:
        return {"error": "Неверный пароль! Доступ запрещен."}
    
    try:
        # 3. ЧТЕНИЕ EXCEL ФАЙЛА
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # 4. РАСЧЕТ МЕТРИК (ЗАГЛУШКИ)
        # Здесь пока стоят тестовые цифры, чтобы ты проверил, что связь работает.
        # Потом ты сможешь вписать сюда свои реальные столбцы из таблицы WB.
        total_revenue = 150000 
        net_profit = 45000     
        best_product = "Тестовый товар (Демо)" 

        # Пример того, как потом считать реальные данные (убери решетки '#'):
        # if 'Сумма продаж' in df.columns:
        #     total_revenue = df['Сумма продаж'].sum()
        
        # 5. ОТВЕТ ИИ-АГЕНТА
        ai_text = "Отчет загружен успешно! Сервер работает отлично."
        if user_query:
            ai_text = f"Ваш вопрос: «{user_query}»\n\nЭто тестовый ответ ИИ. Связь между Vercel и Render настроена на 100%! Позже сюда можно будет подключить ключ от Gemini или ChatGPT."
        
        # 6. ВОЗВРАТ ДАННЫХ НА САЙТ
        return {
            "total_revenue": total_revenue,
            "net_profit": net_profit,
            "best_product": best_product,
            "ai_response": ai_text
        }
        
    except Exception as e:
        # Если файл битый или не читается, сайт покажет эту ошибку
        return {"error": f"Ошибка при чтении Excel: {str(e)}"}
