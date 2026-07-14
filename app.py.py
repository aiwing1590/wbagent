import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# Настройка страницы
st.set_page_config(page_title="WB AI Agent", layout="wide")

# --- КАСТОМНЫЙ CSS СТИЛЬ (Фиолетовый WB-стиль + все анимации) ---
st.markdown("""
    <style>
    /* Основной фон приложения и тексты */
    .stApp {
        background-color: #0d0e15;
        color: #e2e8f0;
    }
    
    /* Стилизация вкладок (Tabs) */
    button[data-baseweb="tab"] {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #a0aec0 !important;
        border-bottom: 2px solid transparent !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #bc7af9 !important;
        border-bottom: 2px solid #bc7af9 !important;
    }
    
    /* Красивые закругленные карточки для метрик */
    div[data-testid="stMetric"] {
        background-color: #161925;
        border: 1px solid #2d3142;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s, border-color 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #bc7af9;
    }
    
    /* Подсветка цифр метрик */
    div[data-testid="stMetricValue"] {
        color: #bc7af9 !important;
        font-size: 26px !important;
        font-weight: 700 !important;
    }
    
    /* Текст ярлыков метрик */
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 13px !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Кастомные контейнеры */
    div[class*="stElementContainer"] {
        border-radius: 8px;
    }

    /* === СТИЛИ ДЛЯ ЛЕТАЮЩЕГО НЕОНОВОГО ШАРИКА (ЗАГРУЗЧИК ИИ) === */
    .loader-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 35px;
        background-color: #161925;
        border: 1px solid #2d3142;
        border-radius: 16px;
        margin: 20px 0;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
    }
    .loader-track {
        width: 180px;
        height: 6px;
        background-color: #23273a;
        border-radius: 10px;
        position: relative;
        margin-bottom: 20px;
        overflow: visible;
    }
    .glowing-ball {
        width: 18px;
        height: 18px;
        background: radial-gradient(circle, #d8b4fe 0%, #bc7af9 60%, #7b2cbf 100%);
        border-radius: 50%;
        position: absolute;
        top: -6px;
        left: 0;
        box-shadow: 0 0 12px #bc7af9, 0 0 24px #bc7af9, 0 0 36px #7b2cbf;
        animation: fly-back-forth 1.6s ease-in-out infinite alternate;
    }
    .loader-text {
        color: #bc7af9;
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        animation: pulse-text 1.6s ease-in-out infinite alternate;
    }
    @keyframes fly-back-forth {
        0% { left: 0%; transform: translateX(0); }
        100% { left: 100%; transform: translateX(-18px); }
    }
    @keyframes pulse-text {
        0% { opacity: 0.4; transform: scale(0.98); }
        100% { opacity: 1; transform: scale(1); }
    }

    /* === СТИЛИ ДЛЯ ЭКРАНА ЛОГИНА === */
    .login-card {
        background-color: #161925;
        border: 1px solid #2d3142;
        padding: 45px 35px;
        border-radius: 24px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.6), 0 0 30px rgba(188, 122, 249, 0.15);
        text-align: center;
        margin-top: 10vh;
    }
    
    /* Летающий неоновый ключ */
    .floating-key {
        font-size: 64px;
        display: inline-block;
        margin-bottom: 15px;
        animation: key-float 3s ease-in-out infinite alternate;
        filter: drop-shadow(0 0 15px #bc7af9);
    }
    @keyframes key-float {
        0% {
            transform: translateY(0px) rotate(-10deg);
        }
        100% {
            transform: translateY(-20px) rotate(10deg);
        }
    }
    
    .login-title {
        color: #ffffff !important;
        font-size: 30px !important;
        font-weight: 800 !important;
        margin-bottom: 5px !important;
        background: linear-gradient(45deg, #ffffff, #bc7af9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .login-subtitle {
        color: #94a3b8 !important;
        font-size: 14px !important;
        margin-bottom: 30px !important;
    }
    
    /* Кастомная красивая строчка ввода пароля */
    div[data-testid="stTextInput"] input {
        background-color: #0d0e15 !important;
        border: 2px solid #2d3142 !important;
        color: #ffffff !important;
        text-align: center !important;
        font-size: 18px !important;
        border-radius: 12px !important;
        padding: 14px !important;
        letter-spacing: 4px !important;
        transition: all 0.3s ease-in-out !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #bc7af9 !important;
        box-shadow: 0 0 15px rgba(188, 122, 249, 0.4) !important;
    }
    div[data-testid="stTextInput"] label {
        display: none !important; /* Прячем дефолтную надпись Streamlit над инпутом */
    }
    </style>
""", unsafe_allow_html=True)

# Инициализация ИИ
def get_model():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except:
        return False

model_configured = get_model()

# --- КРАСИВАЯ АВТОРИЗАЦИЯ ПО ЦЕНТРУ ---
if 'password_correct' not in st.session_state: 
    st.session_state.password_correct = False

if not st.session_state.password_correct:
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("""
            <div class="login-card">
                <div class="floating-key">🔑</div>
                <h2 class="login-title">Добро пожаловать</h2>
                <p class="login-subtitle">Введите пароль доступа для входа в WB AI Agent</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Инпут теперь стилизован через CSS, без стандартной подписи сверху
        password = st.text_input("Пароль доступа", type="password", placeholder="••••••")
        
        if password == "wb140":
            st.session_state.password_correct = True
            st.rerun()
        elif password:
            st.markdown("<p style='color: #ef4444; text-align: center; margin-top: 15px; font-weight: bold;'>❌ Неверный пароль. Попробуйте еще раз.</p>", unsafe_allow_html=True)
    st.stop()

# --- ГЛАВНЫЙ ЭКРАН ПРИЛОЖЕНИЯ (Отображается после успешного ввода пароля) ---
st.markdown("<h1 style='color: #ffffff; margin-bottom: 0px;'>📊 ИИ-Аналитик WB <span style='color: #bc7af9; font-size: 20px;'>PRO Edition</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8; margin-top: 0px;'>Загрузите финансовый отчет WB для мгновенного аудита</p>", unsafe_allow_html=True)

file = st.sidebar.file_uploader("📂 Загрузите отчет (.xlsx)", type=["xlsx"])

if file:
    df = pd.read_excel(file)
    st.sidebar.success("✅ Файл успешно загружен!")

    # СЛОВАРЬ СИНОНИМОВ
    keywords_map = {
        'revenue': ['выручка', 'сумма реализации', 'сумма заказов', 'к оплате', 'цена продажи', 'вайлдберриз к оплате', 'переданный товар', 'сумма'],
        'logistics': ['логистика', 'доставка', 'услуги по доставке'],
        'commission': ['комиссия', 'эквайринг', 'вознаграждение'],
        'cost': ['себестоимость'],
        'promo': ['продвижение', 'реклама', 'кампания'],
        'storage': ['хранение'],
        'acceptance': ['приемка', 'платная приемка'],
        'fines': ['штрафы', 'штраф'],
        'returns_cnt': ['возвраты', 'кол-во возвратов'],
        'returns_sum': ['сумма возвратов'],
        'orders_cnt': ['заказы', 'кол-во заказов', 'количество заказов'],
        'product_name': ['наименование', 'товар', 'название товара', 'артикул', 'предмет', 'номенклатура', 'бренд', 'обоснование для оплаты'],
        'date': ['дата', 'день']
    }

    def detect_column(key, exclude_words=None):
        if exclude_words is None: exclude_words = []
        possible_synonyms = keywords_map[key]
        for col in df.columns:
            col_lower = str(col).lower()
            if any(syn in col_lower for syn in possible_synonyms):
                if not any(ex in col_lower for ex in exclude_words):
                    return col
        return None

    found_cols = {}
    for key in keywords_map.keys():
        if key == 'orders_cnt' or key == 'revenue':
            found_cols[key] = detect_column(key, exclude_words=['дата', 'время'])
        else:
            found_cols[key] = detect_column(key)

    # --- СБОР И РАСЧЕТ ДАННЫХ ---
    rev_col = found_cols['revenue']
    total_revenue = df[rev_col].fillna(0).sum() if rev_col else 0

    discovered_expenses = {}
    expense_keys = ['logistics', 'commission', 'cost', 'promo', 'storage', 'acceptance', 'fines']
    
    for k in expense_keys:
        col_name = found_cols[k]
        if col_name:
            discovered_expenses[k] = df[col_name].fillna(0).abs().sum()

    total_expenses_sum = sum(discovered_expenses.values())
    net_profit = total_revenue - total_expenses_sum

    ret_cnt_col = found_cols['returns_cnt']
    ret_sum_col = found_cols['returns_sum']
    ord_cnt_col = found_cols['orders_cnt']

    orders_val = 0
    if ord_cnt_col and pd.api.types.is_numeric_dtype(df[ord_cnt_col]):
        orders_val = df[ord_cnt_col].fillna(0).sum()

    returns_cnt_val = df[ret_cnt_col].fillna(0).sum() if (ret_cnt_col and pd.api.types.is_numeric_dtype(df[ret_cnt_col])) else 0
    returns_sum_val = df[ret_sum_col].fillna(0).sum() if ret_sum_col else 0

    df['Row_Net'] = df[rev_col].fillna(0) if rev_col else 0
    for k in expense_keys:
        c_name = found_cols[k]
        if c_name:
            df['Row_Net'] = df['Row_Net'] - df[c_name].fillna(0).abs()

    # --- ТАБЫ (ВКЛАДКИ) ---
    tab_fin, tab_analyt, tab_ai = st.tabs(["💰 Финансовый дашборд", "📦 Аналитика по товарам", "🤖 ИИ-Ассистент"])

    # ==================== ВКЛАДКА 1: ФИНАНСЫ ====================
    with tab_fin:
        st.markdown("<h3 style='color: #ffffff;'>📈 Главные метрики</h3>", unsafe_allow_html=True)
        
        main_metrics = []
        if rev_col: 
            main_metrics.append(("Выручка", f"{total_revenue:,.0f} ₽"))
        main_metrics.append(("ЧИСТАЯ ПРИБЫЛЬ", f"{net_profit:,.0f} ₽"))
        if orders_val > 0: 
            main_metrics.append(("Заказов", f"{int(orders_val)} шт"))
        if returns_cnt_val > 0: 
            main_metrics.append(("Возвраты", f"{int(returns_cnt_val)} шт"))
        if returns_sum_val > 0: 
            main_metrics.append(("Сумма возвратов", f"{returns_sum_val:,.0f} ₽"))

        if main_metrics:
            cols_main = st.columns(len(main_metrics))
            for idx, (label, val) in enumerate(main_metrics):
                cols_main[idx].metric(label, val)

        if discovered_expenses:
            st.markdown("<br><h3 style='color: #ffffff;'>💸 Расшифровка расходов</h3>", unsafe_allow_html=True)
            expense_labels = {
                'logistics': 'Логистика', 'commission': 'Комиссия', 'cost': 'Себестоимость',
                'promo': 'Реклама/Продвижение', 'storage': 'Хранение', 'acceptance': 'Приемка',
                'fines': 'Штрафы'
            }
            exp_items = list(discovered_expenses.items())
            chunk_size = 4
            for i in range(0, len(exp_items), chunk_size):
                chunk = exp_items[i:i + chunk_size]
                cols_exp = st.columns(len(chunk))
                for idx, (k, val) in enumerate(chunk):
                    cols_exp[idx].metric(expense_labels[k], f"{val:,.0f} ₽")

    # ==================== ВКЛАДКА 2: АНАЛИТИКА ====================
    with tab_analyt:
        name_col = found_cols['product_name']
        date_col = found_cols['date']

        if rev_col and (name_col or date_col):
            st.markdown("<h3 style='color: #ffffff;'>🎯 Эффективность продаж</h3>", unsafe_allow_html=True)
            col_left, col_right = st.columns(2)

            if name_col:
                product_grouped = df.groupby(name_col)['Row_Net'].sum()
                best_prod = product_grouped.idxmax()
                worst_prod = product_grouped.idxmin()
                
                with col_left:
                    with st.container(border=True):
                        st.markdown("<p style='color: #10b981; font-weight: bold; font-size: 16px;'>📈 Самый прибыльный товар</p>", unsafe_allow_html=True)
                        st.write(f"**{best_prod}**")
                        st.metric("Чистая прибыль", f"{product_grouped[best_prod]:,.0f} ₽")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    with st.container(border=True):
                        st.markdown("<p style='color: #ef4444; font-weight: bold; font-size: 16px;'>📉 Самый убыточный товар</p>", unsafe_allow_html=True)
                        st.write(f"**{worst_prod}**")
                        st.metric("Убыток / Прибыль", f"{product_grouped[worst_prod]:,.0f} ₽")

            if date_col:
                df['Clean_Date'] = pd.to_datetime(df[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
                date_grouped = df.groupby('Clean_Date')['Row_Net'].sum()
                
                if not date_grouped.empty:
                    best_day = date_grouped.idxmax()
                    worst_day = date_grouped.idxmin()
                    
                    with col_right:
                        with st.container(border=True):
                            st.markdown("<p style='color: #10b981; font-weight: bold; font-size: 16px;'>📅 Лучший день по продажам</p>", unsafe_allow_html=True)
                            st.write(f"**Дата: {best_day}**")
                            st.metric("Заработано", f"{date_grouped[best_day]:,.0f} ₽")
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        with st.container(border=True):
                            st.markdown("<p style='color: #ef4444; font-weight: bold; font-size: 16px;'>📅 Худший день по продажам</p>", unsafe_allow_html=True)
                            st.write(f"**Дата: {worst_day}**")
                            st.metric("Заработано", f"{date_grouped[worst_day]:,.0f} ₽")
        else:
            st.info("В файле отсутствуют колонки даты или названия товара для глубокой аналитики.")

    # ==================== ВКЛАДКА 3: ИИ И ПОИСК ====================
    with tab_ai:
        st.markdown("<h3 style='color: #ffffff;'>🤖 Быстрые вопросы по отчету</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color: #94a3b8;'>Напишите свой вопрос (например: <i>'Рукомойники сколько принесли'</i>) — если API-ключ временно заблокирован, сработает мгновенный локальный поиск!</p>", unsafe_allow_html=True)
        
        query = st.text_input("Задайте вопрос ИИ-агенту:", placeholder="Введите ваш запрос...")
        
        if query:
            loader_placeholder = st.empty()
            
            loader_placeholder.markdown("""
                <div class="loader-container">
                    <div class="loader-track">
                        <div class="glowing-ball"></div>
                    </div>
                    <div class="loader-text">ИИ-аналитик изучает ваш отчет...</div>
                </div>
            """, unsafe_allow_html=True)
            
            ai_context = f"Данные отчета: Выручка={total_revenue}, Чистая прибыль={net_profit}. "
            for k, v in discovered_expenses.items():
                ai_context += f"Расход {k}={v}. "
            
            ai_context += f"Доступные колонки: {list(df.columns)}. "
            
            models_to_try = ['gemini-2.0-flash', 'gemini-2.5-pro']
            resp_text = None
            errors_log = []
            
            prompt = (
                f"Ты профессиональный ИИ-аналитик маркетплейса WB. Ответь на вопрос пользователя КРАТКО, СТРОГО ПО ДЕЛУ и только на русском языке.\n"
                f"Выведи только чистый, финальный ответ для человека. НЕ используй никаких шаблонов, заголовков вроде 'User Question:', 'Direct Answer:', 'Reasoning:' или технических тегов.\n\n"
                f"Контекст по файлу: {ai_context}\n"
                f"Вопрос пользователя: {query}\n"
                f"Ответ:"
            )
            
            if model_configured:
                for m_name in models_to_try:
                    try:
                        temp_model = genai.GenerativeModel(m_name)
                        resp = temp_model.generate_content(prompt)
                        resp_text = resp.text
                        break
                    except Exception as e:
                        errors_log.append(f"{m_name}: {str(e)}")
                        continue
            
            fallback_text = None
            if not resp_text:
                q = query.lower().strip()
                
                search_cols = []
                name_col_det = found_cols.get('product_name')
                if name_col_det:
                    search_cols.append(name_col_det)
                
                for col in df.columns:
                    if df[col].dtype == 'object' or pd.api.types.is_string_dtype(df[col]):
                        if col not in search_cols:
                            search_cols.append(col)
                
                val_col = found_cols.get('revenue')
                if not val_col:
                    for col in df.columns:
                        col_lower = str(col).lower()
                        if any(syn in col_lower for syn in ['выручк', 'оплат', 'реализ', 'сумм', 'цена']):
                            if pd.api.types.is_numeric_dtype(df[col]):
                                val_col = col
                                break
                
                if search_cols and val_col:
                    stop_words = {
                        'сколько', 'принесли', 'принес', 'продали', 'купили', 'нашли', 'товар', 
                        'товары', 'по', 'за', 'в', 'и', 'для', 'с', 'на', 'выручка', 'прибыль', 'продажи'
                    }
                    
                    raw_words = q.split()
                    search_terms = []
                    for rw in raw_words:
                        clean_word = re.sub(r'[^\w\s]', '', rw).lower()
                        if clean_word and clean_word not in stop_words and len(clean_word) > 2:
                            suffixes = ('и', 'ы', 'а', 'я', 'ов', 'ев', 'ам', 'ям', 'ами', 'ями', 'ах', 'ях', 'у', 'е', 'ом', 'ем')
                            stemmed = clean_word
                            for suff in sorted(suffixes, key=len, reverse=True):
                                if clean_word.endswith(suff) and len(clean_word) - len(suff) > 3:
                                    stemmed = clean_word[:-len(suff)]
                                    break
                            search_terms.append(stemmed)
                    
                    if search_terms:
                        mask = pd.Series([False] * len(df))
                        for col in search_cols:
                            col_series = df[col].astype(str).str.lower()
                            for term in search_terms:
                                mask = mask | col_series.str.contains(term, na=False)
                        
                        matched_df = df[mask]
                        if not matched_df.empty:
                            display_col = name_col_det if name_col_det else search_cols[0]
                            matched_names = matched_df[display_col].unique()
                            
                            item_revenue = matched_df[val_col].fillna(0).sum()
                            item_net = matched_df['Row_Net'].fillna(0).sum() if 'Row_Net' in matched_df.columns else item_revenue
                            item_count = len(matched_df)
                            
                            names_str = ", ".join([str(n) for n in matched_names[:3]])
                            if len(matched_names) > 3:
                                names_str += f" и еще {len(matched_names) - 3} шт."
                                
                            fallback_text = (
                                f"🔍 **Результат локального анализа (так как Google API временно недоступен):**\n\n"
                                f"Найденные товары: **{names_str}** (колонка: *\"{display_col}\"*)\n"
                                f"* **Количество продаж (строк):** {item_count} шт.\n"
                                f"* **Выручка по найденным позициям:** {item_revenue:,.0f} ₽\n"
                                f"* **Чистая прибыль по найденным позициям (с учетом расходов):** {item_net:,.0f} ₽"
                            )
                
                if not fallback_text:
                    if any(w in q for w in ['выручк', 'оборот', 'всего продали']):
                        fallback_text = f"📊 **Локальный результат:** Общая выручка по всему отчету составляет **{total_revenue:,.0f} ₽**."
                    elif any(w in q for w in ['чистая прибыль', 'прибыль', 'заработал']):
                        fallback_text = f"📊 **Локальный результат:** Общая чистая прибыль по отчету составляет **{net_profit:,.0f} ₽**."

            loader_placeholder.empty()

            if resp_text:
                st.markdown("<div style='background-color: #161925; padding: 20px; border-radius: 12px; border: 1px solid #bc7af9;'>", unsafe_allow_html=True)
                st.write(resp_text)
                st.markdown("</div>", unsafe_allow_html=True)
            elif fallback_text:
                st.markdown(f"<div style='background-color: #161925; padding: 20px; border-radius: 12px; border: 1px solid #eab308; margin-bottom: 15px;'>{fallback_text}</div>", unsafe_allow_html=True)
                st.warning("⚠️ **Внимание:** Этот ответ рассчитан локальным кодом без участия ИИ, так как ваш API-ключ заблокирован со стороны Google. Как только вы обновите API-ключ в secrets, ИИ снова заработает на полную мощность.")
                with st.expander("Посмотреть технический лог ошибок API"):
                    for err in errors_log:
                        st.write(f"❌ {err}")
            else:
                st.error("Не удалось связаться с ИИ и не удалось найти совпадений локально. Лог ошибок по моделям:")
                for err in errors_log:
                    st.write(f"❌ {err}")
else:
    st.info("👈 Пожалуйста, загрузите ваш Excel-отчет Wildberries в боковое меню слева, чтобы начать анализ.")
