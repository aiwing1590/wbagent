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
    
    # Расходы и возвраты
    expenses_cols = ['Комиссия', 'Эквайринг', 'Логистика', 'Хранение', 'Платная приемка', 'Продвижение', 'Штрафы', 'Себестоимость']
    
    # Считаем показатели
    rev = df['Сумма заказов (из ленты в API)'].fillna(0).sum()
    sums = {col: df[col].fillna(0).abs().sum() if col in df.columns else 0 for col in expenses_cols}
    ret_count = df['Возвраты'].fillna(0).sum() if 'Возвраты' in df.columns else 0
    ret_sum = df['Сумма возвратов'].fillna(0).sum() if 'Сумма возвратов' in df.columns else 0
    
    # Чистая прибыль = Выручка минус все расходы
    net_profit = rev - sum(sums.values())
    
    # 1. МЕТРИКИ
    st.subheader("💰 Финансовые показатели")
    cols1 = st.columns(4)
    cols1[0].metric("Выручка", f"{rev:,.0f} ₽")
    cols1[1].metric("ЧИСТАЯ ПРИБЫЛЬ", f"{net_profit:,.0f} ₽")
    cols1[2].metric("Возвраты (кол-во)", f"{int(ret_count)}")
    cols1[3].metric("Сумма возвратов", f"{ret_sum:,.0f} ₽")
    
    # 2. АНАЛИЗ ТОВАРОВ
    df['Чистая'] = df['Сумма заказов (из ленты в API)'].fillna(0)
    for col in expenses_cols:
        if col in df.columns:
            df['Чистая'] = df['Чистая'] - df[col].fillna(0).abs()
            
    st.subheader("📦 Анализ эффективности")
    
    best = df.loc[df['Чистая'].idxmax()]
    worst = df.loc[df['Чистая'].idxmin()]
    
    # Данные для метрик
    best_name = str(best.get('Наименование', 'Товар'))[:25] + "..."
    best_sales_str = f"Продаж: {int(best.get('Заказы (из ленты в API)', 0))}"
    
    worst_name = str(worst.get('Наименование', 'Товар'))[:25] + "..."
    worst_sales_str = f"Продаж: {int(worst.get('Заказы (из ленты в API)', 0))}"
    
    # Вывод метрик без цветных стрелок (delta=None)
    col_a, col_b = st.columns(2)
    col_a.metric("Лучший товар", best_name, best_sales_str, delta=None)
    col_b.metric("Лучший день", str(best.get('Дата', '—')), delta=None)
    
    col_c, col_d = st.columns(2)
    col_c.metric("Худший товар", worst_name, worst_sales_str, delta=None)
    col_d.metric("Худший день", str(worst.get('Дата', '—')), delta=None)

    # ИИ
    st.markdown("---")
    if model:
        query = st.text_input("🤖 Спросить ИИ-агента:")
        if query:
            with st.spinner("Анализирую..."):
                resp = model.generate_content(f"Вопрос: {query}. Прибыль: {net_profit}")
                st.write(resp.text)
