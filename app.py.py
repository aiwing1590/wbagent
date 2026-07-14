import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="WB AI Agent Analyzer", layout="wide")

# Инициализация ИИ
def get_model():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        # Используем более стабильную модель
        return genai.GenerativeModel('gemini-1.5-pro')
    except:
        return None

model = get_model()

# Функция проверки пароля
def check_password():
    if st.session_state.get("password_correct", False): return True
    st.header("🔐 Вход")
    col2 = st.columns([1, 2, 1])[1]
    with col2:
        st.text_input("Логин", key="username")
        st.text_input("Пароль", type="password", key="password")
        if st.button("Войти"):
            if st.session_state["username"] == "ceoprof" and st.session_state["password"] == "wb140":
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("❌ Ошибка")
    return False

if not check_password(): st.stop()

st.title("📊 ИИ-Агент: Аналитик маркетплейсов")
uploaded_file = st.sidebar.file_uploader("Загрузите отчет", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("Данные загружены!")
    
    # Основные метрики
    cols = st.columns(5)
    cols[0].metric("Заказы", f"{df['Заказы (из ленты в API)'].sum():,}")
    cols[1].metric("Сумма", f"{df['Сумма заказов (из ленты в API)'].sum():,.0f} ₽")
    cols[2].metric("Штрафы", f"{df['Штрафы'].sum() if 'Штрафы' in df.columns else 0:,.0f} ₽")
    cols[3].metric("Реклама", f"{df['Реклама'].sum() if 'Реклама' in df.columns else 0:,.0f} ₽")
    cols[4].metric("Возвраты", f"{df['Возвраты заказов'].sum() if 'Возвраты заказов' in df.columns else 0}")
    
    st.markdown("---")
    
    # Аналитика по дням
    st.markdown("### 📅 Анализ по дням")
    if 'Дата' in df.columns:
        daily_sales = df.groupby('Дата')['Сумма заказов (из ленты в API)'].sum()
        col_a, col_b = st.columns(2)
        col_a.metric("Лучший день", f"{daily_sales.max():,.0f} ₽", help=str(daily_sales.idxmax()))
        col_b.metric("Худший день", f"{daily_sales.min():,.0f} ₽", help=str(daily_sales.idxmin()))
    else:
        st.info("Колонка 'Дата' не найдена в файле.")

    st.markdown("---")
    
    # Работа ИИ
    if model:
        query = st.text_input("🤖 Спросить ИИ-агента:")
        if query:
            try:
                with st.spinner("Думаю..."):
                    stats = f"Заказы: {df['Заказы (из ленты в API)'].sum()}, Сумма: {df['Сумма заказов (из ленты в API)'].sum()}"
                    resp = model.generate_content(f"Вопрос: {query}. Статистика: {stats}")
                    st.write(resp.text)
            except Exception as e:
                st.error(f"Ошибка ИИ: {e}")
    else:
        st.warning("⚠️ ИИ недоступен. Проверьте GOOGLE_API_KEY в настройках Secrets.")
