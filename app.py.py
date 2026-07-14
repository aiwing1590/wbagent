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

st.title("📊 ИИ-Аналитик WB (PRO)")
file = st.sidebar.file_uploader("Загрузите отчет", type=["xlsx"])

if file:
    df = pd.read_excel(file)
    
    # Расходы
    expenses_cols = ['Комиссия', 'Эквайринг', 'Логистика', 'Хранение', 'Платная приемка', 'Продвижение', 'Штрафы', 'Себестоимость']
    
    # Считаем суммы
    rev = df['Сумма заказов (из ленты в API)'].fillna(0).sum()
    sums = {col: df[col].fillna(0).abs().sum() if col in df.columns else 0 for col in expenses_cols}
    
    # ЧИСТАЯ ПРИБЫЛЬ = Выручка минус все расходы
    net_profit = rev - sum(sums.values())
    
    # 1. МЕТРИКИ
    st.subheader("💰 Финансовые показатели")
    cols1 = st.columns(4)
    cols1[0].metric("Выручка", f"{rev:,.0f} ₽")
    cols1[1].metric("ЧИСТАЯ ПРИБЫЛЬ", f"{net_profit:,.0f} ₽")
    cols1[2].metric("Себестоимость", f"{sums['Себестоимость']:,.0f} ₽")
    cols1[3].metric("Комиссия", f"{sums['Комиссия']:,.0f} ₽")
    
    cols2 = st.columns(4)
    cols2[0].metric("Логистика", f"{sums['Логистика']:,.0f} ₽")
    cols2[1].metric("Продвижение", f"{sums['Продвижение']:,.0f} ₽")
    cols2[2].metric("Эквайринг", f"{sums['Эквайринг']:,.0f} ₽")
    cols2[3].metric("Штрафы", f"{sums['Штрафы']:,.0f} ₽")

    # 2. АНАЛИЗ (Товары + Лучший/Худший день)
    df['Чистая'] = df['Сумма заказов (из ленты в API)'].fillna(0)
    for col in expenses_cols:
        if col in df.columns:
            df['Чистая'] = df['Чистая'] - df[col].fillna(0).abs()
            
    st.subheader("📦 Анализ эффективности")
    
    # Товары
    best_item = df.loc[df['Чистая'].idxmax()]
    worst_item = df.loc[df['Чистая'].idxmin()]
    
    # Дни (если есть дата)
    date_col = 'Дата' if 'Дата' in df.columns else None
    best_day = best_item[date_col] if date_col else "—"
    worst_day = worst_item[date_col] if date_col else "—"
    
    col_a, col_b = st.columns(2)
    col_a.metric("Лучший товар", str(best_item['Наименование'])[:20]+"...", f"{best_item['Чистая']:,.0f} ₽")
    col_b.metric("Лучший день", f"{best_day}", f"{best_item['Чистая']:,.0f} ₽")
    
    col_c, col_d = st.columns(2)
    col_c.metric("Худший товар", str(worst_item['Наименование'])[:20]+"...", f"{worst_item['Чистая']:,.0f} ₽")
    col_d.metric("Худший день", f"{worst_day}", f"{worst_item['Чистая']:,.0f} ₽")

    # ИИ
    st.markdown("---")
    if model:
        query = st.text_input("🤖 Спросить ИИ-агента:")
        if query:
            with st.spinner("Анализирую..."):
                resp = model.generate_content(f"Вопрос: {query}. Данные: Прибыль {net_profit}, Лучший товар {best_item['Наименование']}")
                st.write(resp.text)
