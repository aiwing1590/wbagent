import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="WB AI Agent Analyzer", layout="wide")

# Берем ключ из защищенного раздела Secrets в Streamlit
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    ai_available = True
except:
    ai_available = False

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
    
    cols = st.columns(4)
    cols[0].metric("Заказы (шт)", f"{df['Заказы (из ленты в API)'].sum():,}")
    cols[1].metric("Сумма", f"{df['Сумма заказов (из ленты в API)'].sum():,.0f} ₽")
    
    if ai_available:
        st.markdown("---")
        query = st.text_input("🤖 Спросить ИИ-агента:")
        if query:
            with st.spinner("Думаю..."):
                prompt = f"Вопрос: {query}. Сумма заказов: {df['Сумма заказов (из ленты в API)'].sum()}"
                resp = model.generate_content(prompt)
                st.write(resp.text)
    else:
        st.warning("ИИ временно недоступен (не настроен ключ API).")
