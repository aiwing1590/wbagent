import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="WB AI Agent Analyzer", layout="wide")

# Инициализация ИИ
def get_model():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-1.5-pro')
    except:
        return None

model = get_model()

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
    
    # 1. Расчет чистой прибыли (Выручка - Штрафы - Реклама)
    # Если каких-то колонок нет, они считаются за 0
    rev = df['Сумма заказов (из ленты в API)'].sum()
    shtraf = df['Штрафы'].sum() if 'Штрафы' in df.columns else 0
    reklama = df['Реклама'].sum() if 'Реклама' in df.columns else 0
    profit = rev - shtraf - reklama
    
    # 2. Метрики
    cols = st.columns(5)
    cols[0].metric("Заказы", f"{df['Заказы (из ленты в API)'].sum():,}")
    cols[1].metric("Выручка", f"{rev:,.0f} ₽")
    cols[2].metric("Чистая прибыль", f"{profit:,.0f} ₽")
    cols[3].metric("Штрафы", f"{shtraf:,.0f} ₽")
    cols[4].metric("Реклама", f"{reklama:,.0f} ₽")
    
    # 3. Лучший/Худший день (ищем по любой колонке, где есть дата или просто по строкам)
    # Если в таблице нет даты, берем индекс строки как "день"
    df['Чистая'] = df['Сумма заказов (из ленты в API)'] - (df['Штрафы'] if 'Штрафы' in df.columns else 0) - (df['Реклама'] if 'Реклама' in df.columns else 0)
    
    st.markdown("### 📈 Анализ эффективности")
    col_a, col_b = st.columns(2)
    col_a.metric("Лучший день (по прибыли)", f"{df['Чистая'].max():,.0f} ₽")
    col_b.metric("Худший день (по прибыли)", f"{df['Чистая'].min():,.0f} ₽")

    st.markdown("---")
    
    # Работа ИИ
    if model:
        query = st.text_input("🤖 Спросить ИИ-агента:")
        if query:
            with st.spinner("Думаю..."):
                # Отправляем ИИ данные для анализа
                summary = f"Общая выручка: {rev}, Штрафы: {shtraf}, Реклама: {reklama}, Прибыль: {profit}"
                resp = model.generate_content(f"Вопрос: {query}. Краткая статистика: {summary}")
                st.write(resp.text)
    else:
        st.warning("⚠️ ИИ недоступен. Проверьте API-ключ в настройках.")
