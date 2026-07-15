from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import re
import sys

app = FastAPI()

# НАСТРОЙКА БЕЗОПАСНОСТИ (CORS)
# Позволяет твоему фронтенду на Vercel без ограничений забирать данные
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === ТВОЙ ПАРОЛЬ ДЛЯ ВХОДА ===
SECRET_PASSWORD = "123"

# СЛОВАРЬ СИНОНИМОВ ДЛЯ УМНОГО КЛАССИФИКАТОРА КОЛОНОК
keywords_map = {
    'revenue': ['валовая выручка', 'выручка по заказам', 'выручка', 'сумма реализации', 'сумма заказов', 'к оплате', 'цена продажи', 'вайлдберриз к оплате', 'переданный товар', 'сумма'],
    'logistics': ['логистика', 'доставка', 'услуги по доставке'],
    'commission': ['комиссия', 'эквайринг', 'вознаграждение'],
    'cost': ['себестоимость'],
    'promo': ['продвижение', 'реклама', 'кампания'],
    'storage': ['хранение'],
    'acceptance': ['приемка', 'платная приемка'],
    'fines': ['штрафы', 'штраф'],
    'returns_cnt': ['возвраты', 'возвраты заказов', 'кол-во возвратов'],
    'returns_sum': ['сумма возвратов', 'сумма отмен'],
    'orders_cnt': ['заказы', 'кол-во заказов', 'количество заказов', 'заказы (из ленты в api)'],
    'product_name': ['наименование', 'товар', 'название товара', 'артикул', 'предмет', 'номенклатура', 'бренд', 'обоснование для оплаты'],
    'date': ['дата', 'день']
}

def detect_column(df, key, exclude_words=None):
    if exclude_words is None: 
        exclude_words = []
    possible_synonyms = keywords_map[key]
    for col in df.columns:
        col_lower = str(col).lower().strip()
        if any(syn in col_lower for syn in possible_synonyms):
            if not any(ex in col_lower for ex in exclude_words):
                return col
    return None

@app.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    app_password: str = Form(...),
    user_query: str = Form(None)
):
    # 1. ПРОВЕРКА ПАРОЛЯ
    if app_password != SECRET_PASSWORD:
        print("LOG: Ошибка авторизации. Неверный пароль.")
        return {"error": "Неверный пароль! Доступ запрещен."}
    
    try:
        # 2. ЧТЕНИЕ ФАЙЛА
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        print("LOG: Файл успешно прочитан. Колонки в таблице:")
        print(list(df.columns))
        
        # Автоопределение колонок по словарю синонимов
        found_cols = {}
        for key in keywords_map.keys():
            if key in ['orders_cnt', 'revenue']:
                found_cols[key] = detect_column(df, key, exclude_words=['дата', 'время'])
            else:
                found_cols[key] = detect_column(df, key)

        print("LOG: Определенные колонки:")
        print(found_cols)

        # 3. ВЫЧИСЛЕНИЯ
        rev_col = found_cols['revenue']
        # Если найдена колонка, берем сумму. Если нет, ставим 0.
        total_revenue = float(df[rev_col].fillna(0).sum()) if rev_col else 0.0

        discovered_expenses = {}
        expense_keys = ['logistics', 'commission', 'cost', 'promo', 'storage', 'acceptance', 'fines']
        for k in expense_keys:
            col_name = found_cols[k]
            if col_name:
                discovered_expenses[k] = float(df[col_name].fillna(0).abs().sum())
            else:
                discovered_expenses[k] = 0.0

        total_expenses_sum = sum(discovered_expenses.values())
        net_profit = total_revenue - total_expenses_sum

        print(f"LOG: Выручка = {total_revenue}, Расходы = {total_expenses_sum}, Прибыль = {net_profit}")

        # Подсчет чистой прибыли по каждой строке
        df['Row_Net'] = df[rev_col].fillna(0) if rev_col else 0.0
        for k in expense_keys:
            c_name = found_cols[k]
            if c_name:
                df['Row_Net'] = df['Row_Net'] - df[c_name].fillna(0).abs()

        # Топ-товар по чистой прибыли
        name_col = found_cols['product_name']
        best_product = "Не определен"
        if name_col:
            product_grouped = df.groupby(name_col)['Row_Net'].sum()
            if not product_grouped.empty:
                best_product = str(product_grouped.idxmax())

        # Определение лучшего дня
        date_col = found_cols['date']
        best_day_info = "Нет данных по датам"
        if date_col:
            df['Clean_Date'] = pd.to_datetime(df[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
            date_grouped = df.groupby('Clean_Date')['Row_Net'].sum()
            if not date_grouped.empty:
                best_day = date_grouped.idxmax()
                best_day_profit = date_grouped[best_day]
                best_day_info = f"{best_day} ({best_day_profit:,.0f} ₽)"

        # 4. ОБРАБОТКА ПОИСКОВЫХ ЗАПРОСОВ К ИИ
        ai_response = ""
        if user_query:
            q = user_query.lower().strip()
            print(f"LOG: Получен вопрос от пользователя: '{user_query}'")
            
            # Локальные быстрые ответы по формулам
            if "топ" in q or "top" in q or "лучш" in q:
                if name_col:
                    product_grouped = df.groupby(name_col)['Row_Net'].sum()
                    top_prods = product_grouped.nlargest(3)
                    ai_response = "📈 **Топ-3 товара по чистой прибыли:**\n\n"
                    for rank, (p_name, p_profit) in enumerate(top_prods.items(), 1):
                        ai_response += f"{rank}. **{p_name}**: {p_profit:,.0f} ₽\n"
                else:
                    ai_response = "Не удалось автоматически определить колонку с наименованием товара."
            
            elif "доля" in q or "логистик" in q or "процент" in q:
                log_val = discovered_expenses.get('logistics', 0.0)
                if total_revenue > 0 and log_val > 0:
                    share = (log_val / total_revenue) * 100
                    ai_response = (
                        f"💸 **Доля расходов на логистику:**\n\n"
                        f"* **Общая выручка:** {total_revenue:,.0f} ₽\n"
                        f"* **Расходы на логистику:** {log_val:,.0f} ₽\n"
                        f"* **Доля от выручки:** **{share:.2f}%**\n\n"
                        f"*(Рекомендуемая норма на WB: до 15-20% от выручки)*"
                    )
                else:
                    ai_response = "В загруженном файле не найдена колонка расходов на доставку или выручка равна нулю."
            
            elif "аудит" in q or "совет" in q or "анализ" in q or "отчет" in q:
                margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
                ai_response = (
                    f"🔍 **Финансовый аудит отчета:**\n\n"
                    f"* **Общая выручка:** {total_revenue:,.0f} ₽\n"
                    f"* **Чистая прибыль:** {net_profit:,.0f} ₽\n"
                    f"* **Маржинальность:** **{margin:.2f}%**\n\n"
                    f"💡 **Советы по оптимизации на основе ваших цифр:**\n"
                )
                
                log_val = discovered_expenses.get('logistics', 0.0)
                log_share = (log_val / total_revenue * 100) if total_revenue > 0 else 0
                if log_share > 25:
                    ai_response += f"1. ⚠️ **Логистика ({log_share:.1f}%):** Это высокий показатель. Рассмотрите распределение по региональным складам WB.\n"
                else:
                    ai_response += "1. ✅ **Логистика в норме:** Расходы на доставку стабильны.\n"
                
                comm_val = discovered_expenses.get('commission', 0.0)
                comm_share = (comm_val / total_revenue * 100) if total_revenue > 0 else 0
                if comm_share > 18:
                    ai_response += f"2. ⚠️ **Комиссия WB ({comm_share:.1f}%):** Высокий процент. Проверьте участие в принудительных акциях.\n"
                else:
                    ai_response += "2. ✅ **Комиссия стабильна:** Процент удержания в норме.\n"
            
            else:
                # Базовый текстовый поиск по названиям товаров
                search_cols = [name_col] if name_col else []
                for col in df.columns:
                    if df[col].dtype == 'object' and col not in search_cols:
                        search_cols.append(col)
                
                stop_words = {'сколько', 'принесли', 'принес', 'продали', 'товар', 'выручка', 'прибыль'}
                raw_words = q.split()
                search_terms = [re.sub(r'[^\w\s]', '', rw).lower() for rw in raw_words if rw.lower() not in stop_words and len(rw) > 2]
                
                if search_terms and search_cols:
                    mask = pd.Series([False] * len(df))
                    for col in search_cols:
                        col_series = df[col].astype(str).str.lower()
                        for term in search_terms:
                            mask = mask | col_series.str.contains(term, na=False)
                    
                    matched_df = df[mask]
                    if not matched_df.empty:
                        item_revenue = float(matched_df[rev_col].fillna(0).sum()) if rev_col else 0.0
                        item_net = float(matched_df['Row_Net'].fillna(0).sum())
                        ai_response = (
                            f"🔍 **Результаты поиска:**\n\n"
                            f"* **Выручка по найденным строкам:** {item_revenue:,.0f} ₽\n"
                            f"* **Чистая прибыль по найденным строкам:** {item_net:,.0f} ₽"
                        )
                
                if not ai_response:
                    ai_response = "Задайте более точный вопрос (например, 'топ', 'аудит', 'доля логистики' или точное название товара)."

        # 5. ОТПРАВЛЯЕМ ПОЛУЧЕННЫЕ РЕАЛЬНЫЕ МЕТРИКИ НА САЙТ
        return {
            "total_revenue": total_revenue,
            "net_profit": net_profit,
            "best_product": f"{best_product} | Лучший день: {best_day_info}",
            "ai_response": ai_response
        }

    except Exception as e:
        print(f"LOG ERROR: Ошибка при обработке Excel: {str(e)}")
        return {"error": f"Ошибка при анализе Excel: {str(e)}"}
