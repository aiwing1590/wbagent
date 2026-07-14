import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="WB AI Agent", layout="wide")

# Инициализация ИИ
def get_model():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except:
        return False

model_configured = get_model()

# Авторизация
if 'password_correct' not in st.session_state: st.session_state.password_correct = False
if not st.session_state.password_correct:
    st.header("🔐 Вход")
    if st.text_input("Пароль", type="password") == "wb140":
        st.session_state.password_correct = True
        st.rerun()
    st.stop()

st.title("📊 ИИ-Аналитик WB (PRO)")
file = st.sidebar.file_uploader("Загрузите отчет", type=["xlsx"])

if file:
    df = pd.read_excel(file)
    st.success("Данные успешно загружены и проанализированы!")

    # СЛОВАРЬ СИНОНИМОВ (Умный поиск колонок по ключевым словам)
    keywords_map = {
        'revenue': ['выручка', 'сумма реализации', 'сумма заказов', 'к оплате', 'цена продажи'],
        'logistics': ['логистика', 'доставка'],
        'commission': ['комиссия', 'эквайринг'],
        'cost': ['себестоимость'],
        'promo': ['продвижение', 'реклама', 'кампания'],
        'storage': ['хранение'],
        'acceptance': ['приемка'],
        'fines': ['штрафы', 'штраф'],
        'returns_cnt': ['возвраты', 'кол-во возвратов'],
        'returns_sum': ['сумма возвратов'],
        'orders_cnt': ['заказы', 'кол-во заказов', 'количество заказов'],
        'product_name': ['наименование', 'товар', 'название товара', 'артикул'],
        'date': ['дата', 'день']
    }

    # Функция динамического определения реального имени колонки в файле
    def detect_column(key, exclude_words=None):
        if exclude_words is None: exclude_words = []
        possible_synonyms = keywords_map[key]
        for col in df.columns:
            col_lower = str(col).lower()
            # Проверяем вхождение ключевого слова
            if any(syn in col_lower for syn in possible_synonyms):
                # Проверяем, нет ли слов-исключений (например, чтобы дата не попала в заказы)
                if not any(ex in col_lower for ex in exclude_words):
                    return col
        return None

    # Определяем, какие колонки реально существуют в загруженном файле
    found_cols = {}
    for key in keywords_map.keys():
        if key == 'orders_cnt' or key == 'revenue':
            found_cols[key] = detect_column(key, exclude_words=['дата', 'время'])
        else:
            found_cols[key] = detect_column(key)

    # --- СБОР И РАСЧЕТ ДАННЫХ ---
    # Выручка
    rev_col = found_cols['revenue']
    total_revenue = df[rev_col].fillna(0).sum() if rev_col else 0

    # Собираем все обнаруженные расходы динамически
    discovered_expenses = {}
    expense_keys = ['logistics', 'commission', 'cost', 'promo', 'storage', 'acceptance', 'fines']
    
    for k in expense_keys:
        col_name = found_cols[k]
        if col_name:
            # Считаем сумму расхода, переводя отрицательные значения в положительные для наглядности
            discovered_expenses[k] = df[col_name].fillna(0).abs().sum()

    # Чистая прибыль = Выручка минус сумма всех найденных в файле расходов
    total_expenses_sum = sum(discovered_expenses.values())
    net_profit = total_revenue - total_expenses_sum

    # Данные по возвратам и штукам заказов (если есть)
    ret_cnt_col = found_cols['returns_cnt']
    ret_sum_col = found_cols['returns_sum']
    ord_cnt_col = found_cols['orders_cnt']

    # Проверка типов данных для штук заказов, чтобы не упасть на датах
    orders_val = 0
    if ord_cnt_col and pd.api.types.is_numeric_dtype(df[ord_cnt_col]):
        orders_val = df[ord_cnt_col].fillna(0).sum()

    returns_cnt_val = df[ret_cnt_col].fillna(0).sum() if (ret_cnt_col and pd.api.types.is_numeric_dtype(df[ret_cnt_col])) else 0
    returns_sum_val = df[ret_sum_col].fillna(0).sum() if ret_sum_col else 0

    # --- ВЫВОД ФИНАНСОВЫХ МЕТРИК ---
    st.subheader("💰 Финансовые показатели")
    
    # Собираем карточки для первой строки (Базовые метрики)
    main_metrics = []
    if rev_col: main_metrics.append(("Выручка", f"{total_revenue:,.0f} ₽"))
    main_metrics.append(("ЧИСТАЯ ПРИБЫЛЬ", f"{net_profit:,.0f} ₽"))
    if orders_val > 0: main_metrics.append(("Заказов (шт)", f"{int(orders_val)}"))
    if returns_cnt_val > 0: main_metrics.append(("Возвраты (кол-во)", f"{int(returns_cnt_val)}"))
    if returns_sum_val > 0: main_metrics.append(("Сумма возвратов", f"{returns_sum_val:,.0f} ₽"))

    if main_metrics:
        cols_main = st.columns(len(main_metrics))
        for idx, (label, val) in enumerate(main_metrics):
            cols_main[idx].metric(label, val)

    # Строка расходов (выводятся ТОЛЬКО те, которые реально найдены в таблице)
    if discovered_expenses:
        st.markdown("##### Расшифровка расходов из файла:")
        expense_labels = {
            'logistics': 'Логистика', 'commission': 'Комиссия', 'cost': 'Себестоимость',
            'promo': 'Продвижение/Реклама', 'storage': 'Хранение', 'acceptance': 'Платная приемка',
            'fines': 'Штрафы'
        }
        cols_exp = st.columns(len(discovered_expenses))
        for idx, (k, val) in enumerate(discovered_expenses.items()):
            cols_exp[idx].metric(expense_labels[k], f"{val:,.0f} ₽")

    # --- АНАЛИЗ ЭФФЕКТИВНОСТИ (ТОВАРЫ И ДНИ) ---
    name_col = found_cols['product_name']
    date_col = found_cols['date']

    if rev_col and (name_col or date_col):
        st.subheader("📦 Анализ эффективности")
        
        # Рассчитываем динамическую прибыль для каждой строки индивидуально
        df['Row_Net'] = df[rev_col].fillna(0)
        for k in expense_keys:
            c_name = found_cols[k]
            if c_name:
                df['Row_Net'] = df['Row_Net'] - df[c_name].fillna(0).abs()

        col_left, col_right = st.columns(2)

        # Анализ по товарам (если колонка найдена)
        if name_col:
            product_grouped = df.groupby(name_col)['Row_Net'].sum()
            best_prod = product_grouped.idxmax()
            worst_prod = product_grouped.idxmin()
            
            with col_left:
                st.metric(f"📈 Лучший товар ({str(best_prod)[:20]}...)", f"{product_grouped[best_prod]:,.0f} ₽")
                st.metric(f"📉 Худший товар ({str(worst_prod)[:20]}...)", f"{product_grouped[worst_prod]:,.0f} ₽")

        # Анализ по дням (если колонка найдена)
        if date_col:
            # Переводим в дату без времени для красивой группировки
            df['Clean_Date'] = pd.to_datetime(df[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
            date_grouped = df.groupby('Clean_Date')['Row_Net'].sum()
            
            if not date_grouped.empty:
                best_day = date_grouped.idxmax()
                worst_day = date_grouped.idxmin()
                
                with col_right:
                    st.metric(f"📅 Лучший день ({str(best_day)})", f"{date_grouped[best_day]:,.0f} ₽")
                    st.metric(f"📅 Худший день ({str(worst_day)})", f"{date_grouped[worst_day]:,.0f} ₽")

    # --- БЛОК ИСКУССТВЕННОГО ИНТЕЛЛЕКТА ---
    st.markdown("---")
    if model_configured:
        query = st.text_input("🤖 Спросить ИИ-агента по этому отчету:")
        if query:
            with st.spinner("ИИ анализирует структуру и показатели отчета..."):
                # Формируем краткую сводку для контекста ИИ
                ai_context = f"Данные отчета: Выручка={total_revenue}, Чистая прибыль={net_profit}. "
                for k, v in discovered_expenses.items():
                    ai_context += f"Расход {k}={v}. "
                
                # Добавляем список реальных колонок файла, чтобы ИИ знал структуру
                ai_context += f"Доступные колонки в загруженном файле: {list(df.columns)}. "
                
                # Только актуальные и активные модели (без устаревшего хлама)
                models_to_try = ['gemini-2.0-flash', 'gemini-2.5-pro']
                
                resp_text = None
                errors_log = []
                
                # Инструкция строгого формата ответа
                prompt = (
                    f"Ты профессиональный ИИ-аналитик маркетплейса WB. Ответь на вопрос пользователя КРАТКО, СТРОГО ПО ДЕЛУ и только на русском языке.\n"
                    f"Выведи только чистый, финальный ответ для человека. НЕ используй никаких шаблонов, заголовков вроде 'User Question:', 'Direct Answer:', 'Reasoning:' или технических тегов.\n\n"
                    f"Контекст по файлу: {ai_context}\n"
                    f"Вопрос пользователя: {query}\n"
                    f"Ответ:"
                )
                
                for m_name in models_to_try:
                    try:
                        temp_model = genai.GenerativeModel(m_name)
                        resp = temp_model.generate_content(prompt)
                        resp_text = resp.text
                        break
                    except Exception as e:
                        errors_log.append(f"{m_name}: {str(e)}")
                        continue
                
                if resp_text:
                    st.write(resp_text)
                else:
                    st.error("Не удалось связаться с ИИ. Лог ошибок по моделям:")
                    for err in errors_log:
                        st.write(f"❌ {err}")
