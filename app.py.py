import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="WB AI Agent", layout="wide")

# Инициализация ИИ
def get_model():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-1.5-pro')
    except:
        return None

model = get_model()

# Вход
if 'password_correct' not in st.session_state: st.session_state.password_correct = False
if not st.session_state.password_correct:
    st.header("🔐 Вход")
    if st.text_input("Пароль", type="password") == "wb140":
        st.session_state.password_correct = True
        st.rerun()
    st.stop()

st.title("📊 ИИ-Аналитик WB")
file = st.sidebar.file_uploader("Загрузите отчет", type=["xlsx"])

if file:
    df = pd.read_excel(file)
    
    # 1. Расчеты для метрик
    rev = df['Сумма заказов (из ленты в API)'].sum()
    promo = df['Продвижение'].sum()
    acquiring = df['Эквайринг'].sum()
    logistics = df['Логистика'].sum()
    penalties = df['Штрафы'].sum()
    commission = df['Комиссия'].sum()
    
    # Чистая прибыль
    net_profit = rev - (promo + abs(acquiring) + abs(logistics) + abs(penalties) + abs(commission))
    
    # 2. Вывод ВСЕХ метрик
    st.subheader("💰 Финансовые показатели")
    cols1 = st.columns(4)
    cols1[0].metric("Выручка", f"{rev:,.0f} ₽")
    cols1[1].metric("Прибыль", f"{net_profit:,.0f} ₽")
    cols1[2].metric("Логистика", f"{abs(logistics):,.0f} ₽")
    cols1[3].metric("Продвижение", f"{abs(promo):,.0f} ₽")
    
    cols2 = st.columns(3)
    cols2[0].metric("Эквайринг", f"{abs(acquiring):,.0f} ₽")
    cols2[1].metric("Штрафы", f"{abs(penalties):,.0f} ₽")
    cols2[2].metric("Комиссия", f"{abs(commission):,.0f} ₽")

    # 3. Анализ товаров
    df['Чистая'] = df['Сумма заказов (из ленты в API)'] - (df['Продвижение'].abs() + df['Эквайринг'].abs() + df['Логистика'].abs() + df['Штрафы'].abs() + df['Комиссия'].abs())
    
    st.subheader("📦 Анализ товаров")
    col_a, col_b = st.columns(2)
    best = df.loc[df['Чистая'].idxmax()]
    worst = df.loc[df['Чистая'].idxmin()]
    
    col_a.metric("Лучший товар", best['Наименование'][:20] + "...", f"{best['Чистая']:,.0f} ₽")
    col_b.metric("Худший товар", worst['Наименование'][:20] + "...", f"{worst['Чистая']:,.0f} ₽")

    # ИИ
    st.markdown("---")
    if model:
        query = st.text_input("🤖 Спросить ИИ:")
        if query:
            with st.spinner("Анализирую..."):
                resp = model.generate_content(f"Вопрос: {query}. Прибыль: {net_profit}, Лучший: {best['Наименование']}, Худший: {worst['Наименование']}")
                st.write(resp.text)
