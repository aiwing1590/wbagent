import streamlit as st
import pandas as pd
import google.generativeai as genai
import re

# Настройка страницы
st.set_page_config(page_title="WB AI Agent", layout="wide")

# --- КАСТОМНЫЙ АДАПТИВНЫЙ CSS СТИЛЬ (Apple Fonts + Gemini Search + Авто-тема: Фиолетовый/Оранжевый) ---
st.markdown("""
    <style>
    /* Глобальный шрифт Apple для всех элементов интерфейса */
    html, body, .stApp, h1, h2, h3, p, span, button, input, label, div {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "SF Pro", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
    }

    /* Общие стили элементов */
    button[data-baseweb="tab"] {
        font-size: 15px !important;
        font-weight: 500 !important;
        letter-spacing: -0.2px !important;
        border-bottom: 2px solid transparent !important;
    }
    div[data-testid="stMetric"] {
        padding: 15px 20px;
        border-radius: 12px;
        transition: transform 0.2s, border-color 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
    }
    div[data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 12px !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[class*="stElementContainer"] {
        border-radius: 8px;
    }
    div[data-testid="stTextInput"] label {
        display: none !important;
    }

    /* Базовые анимации */
    @keyframes fly-back-forth {
        0% { left: 0%; transform: translateX(0); }
        100% { left: 100%; transform: translateX(-18px); }
    }
    @keyframes pulse-text {
        0% { opacity: 0.4; transform: scale(0.98); }
        100% { opacity: 1; transform: scale(1); }
    }
    @keyframes key-float {
        0% { transform: translateY(0px) rotate(-10deg); }
        100% { transform: translateY(-20px) rotate(10deg); }
    }

    /* Стили загрузчика и карточек */
    .loader-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 35px;
        border-radius: 16px;
        margin: 20px 0;
    }
    .loader-track {
        width: 180px;
        height: 6px;
        border-radius: 10px;
        position: relative;
        margin-bottom: 20px;
    }
    .glowing-ball {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        position: absolute;
        top: -6px;
        left: 0;
        animation: fly-back-forth 1.6s ease-in-out infinite alternate;
    }
    .loader-text {
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        animation: pulse-text 1.6s ease-in-out infinite alternate;
    }
    .login-card {
        border-radius: 24px;
        text-align: center;
        margin-top: 10vh;
        padding: 45px 35px;
    }
    .floating-key {
        font-size: 64px;
        display: inline-block;
        margin-bottom: 15px;
        animation: key-float 3s ease-in-out infinite alternate;
    }
    
    /* Адаптивные кастомные классы для текстов */
    .main-title { font-weight: 700; letter-spacing: -0.5px; margin-bottom: 0px; }
    .main-subtitle { margin-top: 5px; font-size: 15px; }
    .section-title { font-weight: 600; margin-top: 20px; margin-bottom: 15px; }
    .ai-response-box { padding: 20px; border-radius: 12px; margin-top: 15px; }

    /* ======================================================== */
    /* 🟠 СВЕТЛАЯ ТЕМА (Включается если в системе/браузере светлая тема) */
    /* ======================================================== */
    @media (prefers-color-scheme: light) {
        .stApp {
            background-color: #f8fafc;
            color: #0f172a;
        }
        .main-title { color: #0f172a !important; }
        .main-subtitle { color: #64748b !important; }
        .section-title { color: #0f172a !important; }
        
        /* Вкладки */
        button[data-baseweb="tab"] { color: #64748b !important; }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #f97316 !important;
            font-weight: 600 !important;
            border-bottom: 2px solid #f97316 !important;
        }
        
        /* Метрики */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
        }
        div[data-testid="stMetric"]:hover { border-color: #f97316; }
        div[data-testid="stMetricValue"] { color: #f97316 !important; }
        div[data-testid="stMetricLabel"] { color: #64748b !important; }
        
        /* Загрузчик */
        .loader-container {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.04);
        }
        .loader-track { background-color: #e2e8f0; }
        .glowing-ball {
            background: radial-gradient(circle, #ffedd5 0%, #f97316 60%, #ea580c 100%);
            box-shadow: 0 0 12px rgba(249, 115, 22, 0.6);
        }
        .loader-text { color: #f97316; }
        
        /* Экран логина */
        .login-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            box-shadow: 0 15px 35px rgba(0,0,0,0.05), 0 0 30px rgba(249, 115, 22, 0.08);
        }
        .floating-key { filter: drop-shadow(0 0 15px #f97316); }
        .login-title {
            background: linear-gradient(45deg, #0f172a, #f97316);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .login-subtitle { color: #64748b !important; }
        
        /* Ввод пароля */
        div[data-testid="stTextInput"] input[type="password"] {
            background-color: #f1f5f9 !important;
            border: 2px solid #e2e8f0 !important;
            color: #0f172a !important;
        }
        div[data-testid="stTextInput"] input[type="password"]:focus {
            border-color: #f97316 !important;
            box-shadow: 0 0 15px rgba(249, 115, 22, 0.2) !important;
        }
        
        /* Поиск Gemini */
        div[data-testid="stTextInput"] input[type="text"] {
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            color: #0f172a !important;
            border-radius: 28px !important;
            padding: 15px 24px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04) !important;
        }
        div[data-testid="stTextInput"] input[type="text"]:focus {
            border-color: #f97316 !important;
            background-color: #ffffff !important;
            box-shadow: 0 0 20px rgba(249, 115, 22, 0.15), 0 4px 15px rgba(0, 0, 0, 0.04) !important;
        }
        div[data-testid="stTextInput"] input[type="text"]::placeholder { color: #94a3b8 !important; }
        .ai-response-box { background-color: #ffffff; border: 1px solid #f97316; color: #0f172a; }
    }

    /* ======================================================== */
    /* 🟣 ТЕМНАЯ ТЕМА (Включается если в системе/браузере темная тема) */
    /* ======================================================== */
    @media (prefers-color-scheme: dark) {
        .stApp {
            background-color: #0d0e15;
            color: #e2e8f0;
        }
        .main-title { color: #ffffff !important; }
        .main-subtitle { color: #94a3b8 !important; }
        .section-title { color: #ffffff !important; }
        
        /* Вкладки */
        button[data-baseweb="tab"] { color: #a0aec0 !important; }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #bc7af9 !important;
            font-weight: 600 !important;
            border-bottom: 2px solid #bc7af9 !important;
        }
        
        /* Метрики */
        div[data-testid="stMetric"] {
            background-color: #161925;
            border: 1px solid #2d3142;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        }
        div[data-testid="stMetric"]:hover { border-color: #bc7af9; }
        div[data-testid="stMetricValue"] { color: #bc7af9 !important; }
        div[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
        
        /* Загрузчик */
        .loader-container {
            background-color: #161925;
            border: 1px solid #2d3142;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
        }
        .loader-track { background-color: #23273a; }
        .glowing-ball {
            background: radial-gradient(circle, #d8b4fe 0%, #bc7af9 60%, #7b2cbf 100%);
            box-shadow: 0 0 12px #bc7af9, 0 0 24px #bc7af9, 0 0 36px #7b2cbf;
        }
        .loader-text { color: #bc7af9; }
        
        /* Экран логина */
        .login-card {
            background-color: #161925;
            border: 1px solid #2d3142;
            box-shadow: 0 15px 35px rgba(0,0,0,0.6), 0 0 30px rgba(188, 122, 249, 0.15);
        }
        .floating-key { filter: drop-shadow(0 0 15px #bc7af9); }
        .login-title {
            background: linear-gradient(45deg, #ffffff, #bc7af9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .login-subtitle { color: #94a3b8 !important; }
        
        /* Ввод пароля */
        div[data-testid="stTextInput"] input[type="password"] {
            background-color: #0d0e15 !important;
            border: 2px solid #2d3142 !important;
            color: #ffffff !important;
        }
        div[data-testid="stTextInput"] input[type="password"]:focus {
            border-color: #bc7af9 !important;
            box-shadow: 0 0 15px rgba(188, 122, 249, 0.35) !important;
        }
        
        /* Поиск Gemini */
        div[data-testid="stTextInput"] input[type="text"] {
            background-color: #161925 !important;
            border: 1px solid #2d3142 !important;
            color: #ffffff !important;
            border-radius: 28px !important;
            padding: 15px 24px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        }
        div[data-testid="stTextInput"] input[type="text"]:focus {
            border-color: #bc7af9 !important;
            background-color: #1b1e2c !important;
            box-shadow: 0 0 20px rgba(188, 122, 249, 0.25), 0 4px 15px rgba(0, 0, 0, 0.3) !important;
        }
        div[data-testid="stTextInput"] input[type="text"]::placeholder { color: #64748b !important; }
        .ai-response-box { background-color: #161925; border: 1px solid #bc7af9; color: #ffffff; }
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

# --- АВТОРИЗАЦИЯ ПО ЦЕНТРУ ---
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
        
        if password == "wb140":
            st.session_state.password_correct = True
            st.rerun()
        elif password:
            st.markdown("<p style='color: #ef4444; text-align: center; margin-top: 15px; font-weight: 600; font-size: 14px;'>❌ Неверный пароль. Попробуйте еще раз.</p>", unsafe_allow_html=True)
    st.stop()

# --- ГЛАВНЫЙ ЭКРАН ПРИЛОЖЕНИЯ ---
st.markdown("<h1 class="main-title">📊 ИИ-Аналитик WB <span style='font-size: 18px; font-weight: 500; opacity: 0.8;'>PRO Edition</span></h1>", unsafe_allow_html=True)
st.markdown("<p class="main-subtitle">Загрузите финансовый отчет WB для мгновенного аудита</p>", unsafe_allow_html=True)

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
        st.markdown("<h3 class="section-title">📈 Главные метрики</h3>", unsafe_allow_html=True)
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
            st.markdown("<h3 class="section-title">💸 Расшифровка расходов</h3>", unsafe_allow_html=True)
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
            st.markdown("<h3 class="section-title">🎯 Эффективность продаж</h3>", unsafe_allow_html=True)
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

    # ==================== ВКЛАДКА 3 ====================
    with tab_ai:
        st.markdown("<h3 class="section-title">🤖 Спросите ИИ-агента</h3>", unsafe_allow_html=True)
        
        query = st.text_input("Задайте вопрос ИИ-агенту:", placeholder="Введите ваш запрос к отчету (например: Сколько принесла куртка?)...")
        
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
            
            fallback_text = None
            if not resp_text:
                q = query.lower().strip()
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
                                f"🔍 **Локальный анализ (API недоступен):**\n\n"
                                f"Товары: **{', '.join([str(n) for n in matched_names[:3]])}**\n"
                                f"* **Выручка:** {item_revenue:,.0f} ₽\n"
                                f"* **Чистая прибыль:** {item_net:,.0f} ₽"
                            )
            
            loader_placeholder.empty()
            if resp_text:
                st.markdown("<div class="ai-response-box">", unsafe_allow_html=True)
                st.write(resp_text)
                st.markdown("</div>", unsafe_allow_html=True)
            elif fallback_text:
                st.markdown(f"<div class="ai-response-box" style='border-color: #eab308;'>{fallback_text}</div>", unsafe_allow_html=True)
else:
    st.info("👈 Пожалуйста, загрузите ваш Excel-отчет Wildberries в боковое меню слева, чтобы начать анализ.")
