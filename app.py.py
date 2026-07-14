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
    
    # Расчет чистой прибыли для каждой строки
    # (Выручка - все расходы)
    df['Чистая'] = df['Сумма заказов (из ленты в API)'] - (
        df['Продвижение'].abs() + df['Эквайринг'].abs() + 
        df['Логистика'].abs() + df['Штрафы'].abs() + df['Комиссия'].abs()
    )
    
    # Основные показатели
    rev = df['Сумма заказов (из ленты в API)'].sum()
    net_profit = df['Чистая'].sum()
    
    cols = st.columns(4)
    cols[0].metric("Выручка", f"{rev:,.0f} ₽")
    cols[1].metric("Прибыль", f"{net_profit:,.0f} ₽")
    cols[2].metric("Заказы", f"{df['Заказы (из ленты в API)'].sum():,}")
    cols[3].metric("Всего товаров", f"{len(df)}")

    # Аналитика: что показывать (Дату или Наименование товара)
    st.markdown("### 📈 Анализ эффективности")
    col_a, col_b = st.columns(2)
    
    # Если есть Дата — берем её, если нет — берем Наименование
    target_col = 'Дата' if 'Дата' in df.columns else 'Наименование'
    
    best = df.loc[df['Чистая'].idxmax()]
    worst = df.loc[df['Чистая'].idxmin()]
    
    col_a.metric(f"Лучший ({target_col})", f"{best[target_col]}", f"{best['Чистая']:,.0f} ₽")
    col_b.metric(f"Худший ({target_col})", f"{worst[target_col]}", f"{worst['Чистая']:,.0f} ₽")

    # ИИ
    st.markdown("---")
    if model:
        query = st.text_input("🤖 Спросить ИИ:")
        if query:
            with st.spinner("Анализирую..."):
                stats = f"Общая прибыль: {net_profit}, Лучший товар: {best['Наименование']}, Худший: {worst['Наименование']}"
                resp = model.generate_content(f"Вопрос: {query}. Данные: {stats}")
                st.write(resp.text)
    else:
        st.error("Ошибка ИИ: Проверьте API-ключ в Settings.")
