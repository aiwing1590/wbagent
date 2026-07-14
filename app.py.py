import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# Настройка страницы
st.set_page_config(page_title="WB AI Agent", layout="wide")

# --- ЕДИНЫЙ КОСМИЧЕСКИЙ ТЕМНЫЙ СТИЛЬ (Фиолетовый WB + Шрифты Apple + Gemini Search) ---
st.markdown("""
    <style>
    /* Глобальный шрифт Apple для всех элементов интерфейса */
    html, body, .stApp, h1, h2, h3, p, span, button, input, label, div {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "SF Pro", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
    }

    /* Основной глубокий темный фон приложения и тексты */
    .stApp {
        background-color: #0d0e15 !important;
        color: #e2e8f0 !important;
    }
    
    /* Стилизация бокового меню (Sidebar) в темном стиле */
    section[data-testid="stSidebar"] {
        background-color: #0d0e15 !important;
        border-right: 1px solid #2d3142 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stFileUploader"] {
        background-color: #161925 !important;
        border: 1px dashed #2d3142 !important;
        border-radius: 12px !important;
        padding: 10px !important;
    }
    
    /* Стилизация вкладок (Tabs) */
    button[data-baseweb="tab"] {
        font-size: 15px !important;
        font-weight: 500 !important;
        letter-spacing: -0.2px !important;
        color: #a0aec0 !important;
        border-bottom: 2px solid transparent !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #bc7af9 !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #bc7af9 !important;
    }
    
    /* Красивые закругленные карточки для метрик */
    div[data-testid="stMetric"] {
        background-color: #161925 !important;
        border: 1px solid #2d3142 !important;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s, border-color 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #bc7af9 !important;
    }
    
    /* Подсветка цифр метрик */
    div[data-testid="stMetricValue"] {
        color: #bc7af9 !important;
        font-size: 26px !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
    }
    
    /* Текст ярлыков метрик */
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 12px !important;
        font-weight: 500 !important;
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
        font-size: 13px;
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
        0% { transform: translateY(0px) rotate(-10deg); }
        100% { transform: translateY(-20px) rotate(10deg); }
    }
    
    .login-title {
        color: #ffffff !important;
        font-size: 32px !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
        margin-bottom: 5px !important;
        background: linear-gradient(45deg, #ffffff, #bc7af9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .login-subtitle {
        color: #94a3b8 !important;
        font-size: 14px !important;
        font-weight: 400 !important;
        margin-bottom: 30px !important;
    }
    
    /* Скрываем стандартные надписи Streamlit над текстовыми инпутами */
    div[data-testid="stTextInput"] label {
        display: none !important;
    }
    
    /* Строка ввода ПАРОЛЯ */
    div[data-testid="stTextInput"] input[type="password"] {
        background-color: #0d0e15 !important;
        border: 2px solid #2d3142 !important;
        color: #ffffff !important;
        text-align: center !important;
        font-size: 20px !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        padding: 14px !important;
        letter-spacing: 6px !important;
        transition: all 0.25s ease-in-out !important;
    }
    div[data-testid="stTextInput"] input[type="password"]:focus {
        border-color: #bc7af9 !important;
        box-shadow: 0 0 15px rgba(188, 122, 249, 0.35) !important;
    }
    
    /* СТРОКА ПОИСКА В СТИЛЕ GOOGLE GEMINI */
    div[data-testid="stTextInput"] input[type="text"] {
        background-color: #161925 !important;
        border: 1px solid #2d3142 !important;
        color: #ffffff !important;
        text-align: left !important;
        font-size: 16px !important;
        font-weight: 400 !important;
        border-radius: 28px !important; /* Форма капсулы */
        padding: 15px 24px !important; /* Просторные отступы */
        letter-spacing: normal !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div[data-testid="stTextInput"] input[type="text"]:focus {
        border-color: #bc7af9 !important;
        background-color: #1b1e2c !important;
        box-shadow: 0 0 20px rgba(188, 122, 249, 0.25), 0 4px 15px rgba(0, 0, 0, 0.3) !important;
    }
    div[data-testid="stTextInput"] input[type="text"]::placeholder {
        color: #64748b !important;
        opacity: 1;
    }
    
    /* Стилизация Prompt-кнопок под чипсы */
    .stButton > button {
        background-color: #161925 !important;
        color: #a0aec0 !important;
        border: 1px solid #2d3142 !important;
        border-radius: 20px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease-in-out !important;
        padding: 6px 16px !important;
    }
    .stButton > button:hover {
        background-color: #1b1e2c !important;
        border-color: #bc7af9 !important;
        color: #ffffff !important;
        box-shadow: 0 0 10px rgba(188, 122, 249, 0.2) !important;
    }

    /* Оформление кастомных текстовых блоков */
    .main-title { color: #ffffff !important; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 0px; }
    .main-subtitle { color: #94a3b8 !important; margin-top: 5px; font-size: 15px; }
    .section-title { color: #ffffff !important; font-weight: 600; margin-top: 20px; margin-bottom: 15px; }
    .ai-response-box { background-color: #161925; border: 1px solid #bc7af9; color: #ffffff; padding: 20px; border-radius: 12px; margin-top: 15px; }
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

# --- АВТОРИЗАЦИЯ С ЗАЩИТОЙ ЧЕРЕЗ SECRETS ---
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
        
        password = st.text_input("Пароль доступа", type="password", placeholder="••••••")
        
        # Получаем секретный пароль из настроек Streamlit Secrets. Если его нет, по умолчанию будет "wb140"
        correct_password = st.secrets.get("APP_PASSWORD", "wb140")
        
        if password == correct_password:
            st.session_state.password_correct = True
            st.rerun()
        elif password:
            st.markdown("<p style='color: #ef4444; text-align: center; margin-top: 15px; font-weight: 600; font-size: 14px;'>❌ Неверный пароль. Попробуйте еще раз.</p>", unsafe_allow_html=True)
    st.stop()

# --- ГЛАВНЫЙ ЭКРАН ПРИЛОЖЕНИЯ ---
st.markdown("<h1 class='main-title'>📊 ИИ-Аналитик WB <span style='font-size: 18px; font-weight: 500; color: #bc7af9;'>PRO Edition</span></h1>", unsafe_allow_html=True)
st.markdown("<p class='main-subtitle'>Загрузите финансовый отчет WB для мгновенного аудита</p>", unsafe_allow_html=True)

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

    # Расчеты
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

    # Табы
    tab_fin, tab_analyt, tab_ai = st.tabs(["💰 Финансовый дашборд", "📦 Аналитика по товарам", "🤖 ИИ-Ассистент"])

    # ==================== ВКЛАДКА 1 ====================
    with tab_fin:
        st.markdown("<h3 class='section-title'>📈 Главные метрики</h3>", unsafe_allow_html=True)
        main_metrics = []
        if rev_col: main_metrics.append(("Выручка", f"{total_revenue:,.0f} ₽"))
        main_metrics.append(("Чистая прибыль", f"{net_profit:,.0f} ₽"))
        if orders_val > 0: main_metrics.append(("Заказов", f"{int(orders_val)} шт"))
        if returns_cnt_val > 0: main_metrics.append(("Возвраты", f"{int(returns_cnt_val)} шт"))
        if returns_sum_val > 0: main_metrics.append(("Сумма возвратов", f"{returns_sum_val:,.0f} ₽"))

        if main_metrics:
            cols_main = st.columns(len(main_metrics))
            for idx, (label, val) in enumerate(main_metrics):
                cols_main[idx].metric(label, val)

        if discovered_expenses:
            st.markdown("<h3 class='section-title'>💸 Расшифровка расходов</h3>", unsafe_allow_html=True)
            expense_labels = {
                'logistics': 'Логистика', 'commission': 'Комиссия', 'cost': 'Себестоимость',
                'promo': 'Реклама', 'storage': 'Хранение', 'acceptance': 'Приемка', 'fines': 'Штрафы'
            }
            exp_items = list(discovered_expenses.items())
            chunk_size = 4
            for i in range(0, len(exp_items), chunk_size):
                chunk = exp_items[i:i + chunk_size]
                cols_exp = st.columns(len(chunk))
                for idx, (k, val) in enumerate(chunk):
                    cols_exp[idx].metric(expense_labels[k], f"{val:,.0f} ₽")

    # ==================== ВКЛАДКА 2 ====================
    with tab_analyt:
        name_col = found_cols['product_name']
        date_col = found_cols['date']

        if rev_col and (name_col or date_col):
            st.markdown("<h3 class='section-title'>🎯 Эффективность продаж</h3>", unsafe_allow_html=True)
            col_left, col_right = st.columns(2)

            if name_col:
                product_grouped = df.groupby(name_col)['Row_Net'].sum()
                best_prod = product_grouped.idxmax()
                worst_prod = product_grouped.idxmin()
                
                with col_left:
                    with st.container(border=True):
                        st.markdown("<p style='color: #10b981; font-weight: 600; font-size: 15px; margin-bottom: 5px;'>📈 Самый прибыльный товар</p>", unsafe_allow_html=True)
                        st.write(f"**{best_prod}**")
                        st.metric("Чистая прибыль", f"{product_grouped[best_prod]:,.0f} ₽")
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.container(border=True):
                        st.markdown("<p style='color: #ef4444; font-weight: 600; font-size: 15px; margin-bottom: 5px;'>📉 Самый убыточный товар</p>", unsafe_allow_html=True)
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
                            st.markdown("<p style='color: #10b981; font-weight: 600; font-size: 15px; margin-bottom: 5px;'>📅 Лучший день по продажам</p>", unsafe_allow_html=True)
                            st.write(f"**Дата: {best_day}**")
                            st.metric("Заработано", f"{date_grouped[best_day]:,.0f} ₽")
                        st.markdown("<br>", unsafe_allow_html=True)
                        with st.container(border=True):
                            st.markdown("<p style='color: #ef4444; font-weight: 600; font-size: 15px; margin-bottom: 5px;'>📅 Худший день по продажам</p>", unsafe_allow_html=True)
                            st.write(f"**Дата: {worst_day}**")
                            st.metric("Заработано", f"{date_grouped[worst_day]:,.0f} ₽")
        else:
            st.info("В файле отсутствуют колонки даты или названия товара для глубокой аналитики.")

    # ==================== ВКЛАДКА 3 (ИИ И GEMINI-ПОИСК) ====================
    with tab_ai:
        st.markdown("<h3 class='section-title'>🤖 Спросите ИИ-агента</h3>", unsafe_allow_html=True)
        
        # --- БЫСТРЫЕ ШАБЛОНЫ (PROMPT CHIPS) ---
        if 'ai_search_input' not in st.session_state:
            st.session_state.ai_search_input = ""

        def select_chip(text):
            st.session_state.ai_search_input = text

        st.markdown("<p style='font-size: 13px; opacity: 0.7; margin-bottom: 8px;'>Быстрые шаблоны вопросов:</p>", unsafe_allow_html=True)
        
        col_chip1, col_chip2, col_chip3 = st.columns(3)
        with col_chip1:
            st.button("📈 Топ-3 товара по прибыли", use_container_width=True, on_click=select_chip, args=("Покажи топ 3 товара по чистой прибыли",))
        with col_chip2:
            st.button("💸 Доля расходов на логистику", use_container_width=True, on_click=select_chip, args=("Какая доля от общей выручки уходит на логистику?",))
        with col_chip3:
            st.button("🔍 Сделай краткий аудит отчета", use_container_width=True, on_click=select_chip, args=("Сделай общий финансовый аудит этого отчета и дай 3 совета по оптимизации",))

        st.markdown("<br>", unsafe_allow_html=True)

        # Строка поиска Gemini с динамическим значением из чипсов
        query = st.text_input("Задайте вопрос ИИ-агенту:", key="ai_search_input", placeholder="Введите ваш запрос к отчету (например: Сколько принесла куртка?)...")
        
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
                f"Ты профессиональный ИИ-аналитик маркетплейса WB. Ответь на вопрос пользователя КРАТКО, СТРОГО ПО ДЕЛУ.\n"
                f"Выведи только чистый ответ. НЕ используй технические теги или вводные шаблоны.\n\n"
                f"Контекст: {ai_context}\n"
                f"Вопрос: {query}\n"
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
            
            # --- УМНЫЙ ЛОКАЛЬНЫЙ ДВИЖОК АНАЛИТИКИ (ЕСЛИ API ВЫКЛЮЧЕН ИЛИ ДЛЯ МГНОВЕННОГО ОТВЕТА) ---
            fallback_text = None
            if not resp_text:
                q = query.lower().strip()
                
                # 1. Обработка запроса: "Покажи топ 3 товара по чистой прибыли"
                if "топ" in q or "top" in q or "лучш" in q:
                    name_col_det = found_cols.get('product_name')
                    if name_col_det and 'Row_Net' in df.columns:
                        product_grouped = df.groupby(name_col_det)['Row_Net'].sum()
                        top_prods = product_grouped.nlargest(3)
                        fallback_text = "📈 **Локальный анализ — Топ-3 товара по чистой прибыли:**\n\n"
                        for rank, (p_name, p_profit) in enumerate(top_prods.items(), 1):
                            fallback_text += f"{rank}. **{p_name}**: {p_profit:,.0f} ₽\n"
                    else:
                        fallback_text = "Не удалось автоматически определить колонку с наименованием товара в вашем файле."
                
                # 2. Обработка запроса: "Какая доля от общей выручки уходит на логистику?"
                elif "доля" in q or "логистик" in q or "процент" in q:
                    log_val = discovered_expenses.get('logistics', 0)
                    if total_revenue > 0 and log_val > 0:
                        share = (log_val / total_revenue) * 100
                        fallback_text = (
                            f"💸 **Локальный анализ — Доля расходов на логистику:**\n\n"
                            f"* **Общая выручка:** {total_revenue:,.0f} ₽\n"
                            f"* **Расходы на логистику:** {log_val:,.0f} ₽\n"
                            f"* **Доля от выручки:** **{share:.2f}%**\n\n"
                            f"_(Рекомендуемая норма на WB: до 15-20% от выручки)_"
                        )
                    else:
                        fallback_text = "В загруженном файле не найдена колонка расходов на логистику (доставку) или выручка равна нулю."

                # 3. Обработка запроса: "Сделай общий финансовый аудит этого отчета..."
                elif "аудит" in q or "совет" in q or "анализ" in q or "отчет" in q:
                    margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
                    fallback_text = (
                        f"🔍 **Локальный финансовый аудит отчета:**\n\n"
                        f"* **Общая выручка:** {total_revenue:,.0f} ₽\n"
                        f"* **Чистая прибыль:** {net_profit:,.0f} ₽\n"
                        f"* **Маржинальность бизнеса:** **{margin:.2f}%**\n\n"
                        f"💡 **3 совета по оптимизации на основе ваших цифр:**\n"
                    )
                    
                    # Логика динамических советов на основе реальных данных из таблицы
                    log_val = discovered_expenses.get('logistics', 0)
                    log_share = (log_val / total_revenue * 100) if total_revenue > 0 else 0
                    if log_share > 25:
                        fallback_text += f"1. ⚠️ **Оптимизируйте логистику ({log_share:.1f}% от выручки):** Это высокий показатель. Рассмотрите возможность отгрузки на другие региональные склады ближе к покупателям или пересмотрите объемную массу упаковки.\n"
                    else:
                        fallback_text += "1. ✅ **Логистика в норме:** Расходы на доставку стабильны. Продолжайте контролировать оборачиваемость на складах.\n"
                    
                    comm_val = discovered_expenses.get('commission', 0)
                    comm_share = (comm_val / total_revenue * 100) if total_revenue > 0 else 0
                    if comm_share > 18:
                        fallback_text += f"2. ⚠️ **Высокая комиссия WB ({comm_share:.1f}%):** Убедитесь, что вы правильно заложили СПП (скидку постоянного покупателя) и не теряете прибыль при участии в принудительных акциях.\n"
                    else:
                        fallback_text += "2. ✅ **Комиссия стабильна:** Процент удержания площадки находится в пределах плановой нормы.\n"
                    
                    ret_share = (returns_cnt_val / orders_val * 100) if (orders_val > 0 and returns_cnt_val > 0) else 0
                    if ret_share > 20:
                        fallback_text += f"3. ⚠️ **Высокий процент возвратов ({ret_share:.1f}%):** Изучите последние негативные отзывы. Скорее всего, хромает качество упаковки, таблица размеров или есть брак в партии.\n"
                    else:
                        fallback_text += "3. ✅ **Процент возвратов отличный:** Процент выкупа товаров на высоком уровне, качество упаковки соответствует ожиданиям клиентов.\n"

                # 4. Базовый точечный текстовый поиск по названию товара (если спросили конкретное название)
                else:
                    search_cols = []
                    name_col_det = found_cols.get('product_name')
                    if name_col_det: search_cols.append(name_col_det)
                    for col in df.columns:
                        if df[col].dtype == 'object' or pd.api.types.is_string_dtype(df[col]):
                            if col not in search_cols: search_cols.append(col)
                    
                    val_col = found_cols.get('revenue')
                    if search_cols and val_col:
                        stop_words = {'сколько', 'принесли', 'принес', 'продали', 'товар', 'выручка', 'прибыль'}
                        raw_words = q.split()
                        search_terms = [re.sub(r'[^\w\s]', '', rw).lower() for rw in raw_words if rw.lower() not in stop_words and len(rw) > 2]
                        
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
                                
                                fallback_text = (
                                    f"🔍 **Локальный анализ:**\n\n"
                                    f"Найденные товары: **{', '.join([str(n) for n in matched_names[:3]])}**\n"
                                    f"* **Выручка:** {item_revenue:,.0f} ₽\n"
                                    f"* **Чистая прибыль:** {item_net:,.0f} ₽"
                                )
            
            loader_placeholder.empty()
            if resp_text:
                st.markdown(f"<div class='ai-response-box'>{resp_text}</div>", unsafe_allow_html=True)
            elif fallback_text:
                st.markdown(f"<div class='ai-response-box'>{fallback_text}</div>", unsafe_allow_html=True)
else:
    st.info("👈 Пожалуйста, загрузите ваш Excel-отчет Wildberries в боковое меню слева, чтобы начать анализ.")
