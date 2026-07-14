import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="WB AI Agent", layout="wide")

def get_model():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-1.5-pro')
    except:
        return None

model = get_model()

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
    
    # ФУНКЦИЯ ПОИСКА КОЛОНОК (подстраивается под любую таблицу)
    def find_col(possible_names):
        for name in possible_names:
            for col in df.columns:
                if name.lower() in col.lower():
                    return col
        return None

    # Ищем колонки с учетом разных названий
    rev_col = find_col(['выручка', 'сумма реализации', 'сумма заказов'])
    log_col = find_col(['логистика'])
    com_col = find_col(['комиссия'])
    cost_col = find_col(['себестоимость'])
    ret_col = find_col(['возврат'])
    name_col = find_col(['наименование'])
    date_col = find_col(['дата продажи', 'дата заказа'])
    
    # Расчет данных
    rev = df[rev_col].fillna(0).sum() if rev_col else 0
    log = df[log_col].fillna(0).abs().sum() if log_col else 0
    com = df[com_col].fillna(0).abs().sum() if com_col else 0
    cost = df[cost_col].fillna(0).abs().sum() if cost_col else 0
    
    # Прибыль
    net_profit = rev - log - com - cost
    
    # Метрики
    st.subheader("💰 Финансовые показатели")
    cols1 = st.columns(4)
    cols1[0].metric("Выручка", f"{rev:,.0f} ₽")
    cols1[1].metric("ЧИСТАЯ ПРИБЫЛЬ", f"{net_profit:,.0f} ₽")
    cols1[2].metric("Логистика", f"{log:,.0f} ₽")
    cols1[3].metric("Себестоимость", f"{cost:,.0f} ₽")
    
    # Анализ товаров
    st.subheader("📦 Анализ эффективности")
    if name_col:
        # Группируем по товару
        best = df.groupby(name_col)[rev_col].sum().idxmax()
        worst = df.groupby(name_col)[rev_col].sum().idxmin()
        
        col_a, col_b = st.columns(2)
        col_a.metric("Лучший товар", str(best)[:20])
        col_b.metric("Худший товар", str(worst)[:20])
    
    # ИИ
    st.markdown("---")
    if model:
        query = st.text_input("🤖 Спросить ИИ-агента:")
        if query:
            with st.spinner("Анализирую..."):
                resp = model.generate_content(f"Вопрос: {query}. Выручка: {rev}, Прибыль: {net_profit}")
                st.write(resp.text)
