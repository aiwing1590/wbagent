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
    
    # Считаем всё по точным названиям из файла
    orders = df['Заказы (из ленты в API)'].sum()
    revenue = df['Сумма заказов (из ленты в API)'].sum()
    promo = df['Продвижение'].sum()
    acquiring = df['Эквайринг'].sum()
    logistics = df['Логистика'].sum()
    penalties = df['Штрафы'].sum()
    commission = df['Комиссия'].sum()
    
    # Чистая прибыль = Выручка - все расходы
    net_profit = revenue - (promo + abs(acquiring) + abs(logistics) + abs(penalties) + abs(commission))
    
    # Метрики
    cols = st.columns(4)
    cols[0].metric("Выручка", f"{revenue:,.0f} ₽")
    cols[1].metric("Прибыль", f"{net_profit:,.0f} ₽")
    cols[2].metric("Логистика", f"{abs(logistics):,.0f} ₽")
    cols[3].metric("Продвижение", f"{abs(promo):,.0f} ₽")
    
    cols2 = st.columns(3)
    cols2[0].metric("Эквайринг", f"{abs(acquiring):,.0f} ₽")
    cols2[1].metric("Штрафы", f"{abs(penalties):,.0f} ₽")
    cols2[2].metric("Комиссия", f"{abs(commission):,.0f} ₽")

    # ИИ
    if model:
        query = st.text_input("🤖 Спросить ИИ:")
        if query:
            with st.spinner("Анализирую..."):
                stats = f"Выручка: {revenue}, Расходы: Продвижение {promo}, Эквайринг {acquiring}, Логистика {logistics}, Штрафы {penalties}, Комиссия {commission}"
                resp = model.generate_content(f"Вопрос: {query}. Данные: {stats}")
                st.write(resp.text)
    else:
        st.error("Ошибка ИИ: Проверьте API-ключ в Settings -> Secrets.")
