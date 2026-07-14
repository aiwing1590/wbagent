import streamlit as st
import pandas as pd
import google.generativeai as genai
import matplotlib.pyplot as plt

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
    
    # 1. Расходы и расчеты
    expenses_cols = [
        'Комиссия', 'Эквайринг', 'Логистика', 'Хранение', 
        'Платная приемка', 'Продвижение', 'Штрафы', 'Себестоимость'
    ]
    spp_col = 'Скидка WB (СПП)'
    
    rev = df['Сумма заказов (из ленты в API)'].sum() if 'Сумма заказов (из ленты в API)' in df.columns else 0
    spp_val = df[spp_col].sum() if spp_col in df.columns else 0
    
    sums = {}
    for col in expenses_cols:
        sums[col] = df[col].fillna(0).abs().sum() if col in df.columns else 0
            
    # Чистая прибыль = Выручка + СПП - Расходы
    net_profit = rev + spp_val - sum(sums.values())
    
    # 2. Метрики (ЖЕЛЕЗОБЕТОННЫЕ)
    st.subheader("💰 Финансовые показатели")
    cols1 = st.columns(4)
    cols1[0].metric("Выручка", f"{rev:,.0f} ₽")
    cols1[1].metric("ЧИСТАЯ ПРИБЫЛЬ", f"{net_profit:,.0f} ₽")
    cols1[2].metric("СПП (Скидка WB)", f"{spp_val:,.0f} ₽")
    cols1[3].metric("Себестоимость", f"{sums['Себестоимость']:,.0f} ₽")
    
    cols2 = st.columns(4)
    cols2[0].metric("Логистика", f"{sums['Логистика']:,.0f} ₽")
    cols2[1].metric("Продвижение", f"{sums['Продвижение']:,.0f} ₽")
    cols2[2].metric("Эквайринг", f"{sums['Эквайринг']:,.0f} ₽")
    cols2[3].metric("Комиссия", f"{sums['Комиссия']:,.0f} ₽")

    # 3. Анализ товаров и График
    df['Чистая'] = df['Сумма заказов (из ленты в API)'].fillna(0) + df[spp_col].fillna(0)
    for col in expenses_cols:
        if col in df.columns:
            df['Чистая'] = df['Чистая'] - df[col].fillna(0).abs()
            
    st.subheader("📦 Анализ товаров")
    col_a, col_b = st.columns(2)
    
    best = df.loc[df['Чистая'].idxmax()]
    worst = df.loc[df['Чистая'].idxmin()]
    
    col_a.metric("Лучший товар", str(best['Наименование'])[:20]+"...", f"{best['Чистая']:,.0f} ₽")
    col_b.metric("Худший товар", str(worst['Наименование'])[:20]+"...", f"{worst['Чистая']:,.0f} ₽")
    
    # ГРАФИК
    st.markdown("### 📊 Распределение прибыльности товаров")
    fig, ax = plt.subplots(figsize=(10, 4))
    df_sorted = df.sort_values('Чистая', ascending=False).head(15) # Топ 15 товаров
    ax.bar(df_sorted['Наименование'].apply(lambda x: x[:10]+"..."), df_sorted['Чистая'], color='skyblue')
    plt.xticks(rotation=45, ha='right')
    st.pyplot(fig)

    # 4. ИИ
    st.markdown("---")
    if model:
        query = st.text_input("🤖 Спросить ИИ-агента:")
        if query:
            with st.spinner("Анализирую..."):
                resp = model.generate_content(f"Вопрос: {query}. Прибыль: {net_profit}, СПП: {spp_val}, Лучший: {best['Наименование']}")
                st.write(resp.text)
