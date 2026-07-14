import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="WB AI Agent Analyzer", layout="wide")

# Инициализация ИИ
def setup_ai():
    try:
        # Пытаемся получить ключ из секретов Streamlit
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-1.5-flash'), True
    except Exception as e:
        return None, False

model, ai_available = setup_ai()

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
    
    # Расширенные метрики
    cols = st.columns(4)
    cols[0].metric("Заказы (шт)", f"{df['Заказы (из ленты в API)'].sum():,}")
    cols[1].metric("Сумма", f"{df['Сумма заказов (из ленты в API)'].sum():,.0f} ₽")
    
    # Проверяем наличие колонок перед выводом
    val_rev = df['Валовая выручка'].sum() if 'Валовая выручка' in df.columns else 0
    returns = df['Возвраты заказов'].sum() if 'Возвраты заказов' in df.columns else 0
    
    cols[2].metric("Валовая выручка", f"{val_rev:,.0f} ₽")
    cols[3].metric("Возвраты", f"{returns:,} шт.")
    
    st.markdown("---")
    
    if ai_available:
        query = st.text_input("🤖 Спросить ИИ-агента:")
        if query:
            with st.spinner("Думаю..."):
                prompt = f"Вопрос: {query}. Данные: Заказов {df['Заказы (из ленты в API)'].sum()}, Сумма {df['Сумма заказов (из ленты в API)'].sum()}"
                resp = model.generate_content(prompt)
                st.write(resp.text)
    else:
        st.warning("⚠️ ИИ недоступен. Проверьте ключ GOOGLE_API_KEY в настройках Secrets.")
