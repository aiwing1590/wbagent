import streamlit as st
import pandas as pd
from g4f.client import Client

# Настройка страницы
st.set_page_config(page_title="WB AI Agent Analyzer", layout="wide")

# ================= ЗАЩИТА ПАРОЛЕМ =================
def check_password():
    def password_entered():
        if st.session_state["username"] == "ceoprof" and st.session_state["password"] == "wb140":
            st.session_state["password_correct"] = True
            del st.session_state["password"], st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.header("🔐 Вход в WB AI Agent")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.text_input("Логин", key="username")
        st.text_input("Пароль", type="password", key="password")
        st.button("Войти", on_click=password_entered)
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ Неверный логин или пароль!")
    return False

if not check_password():
    st.stop()
# ==================================================

st.title("📊 ИИ-Агент: Аналитик маркетплейсов")

if st.sidebar.button("🚪 Выйти"):
    st.session_state["password_correct"] = False
    st.rerun()

uploaded_file = st.sidebar.file_uploader("Загрузите отчет WB (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    
    # Обработка дат
    if 'Дата заказа' in df.columns:
        df['Дата заказа'] = pd.to_datetime(df['Дата заказа'])
        df['День'] = df['Дата заказа'].dt.date

    st.success("Данные загружены!")
    
    # 1. Блок лучшего дня
    if 'День' in df.columns and 'Сумма заказов (из ленты в API)' in df.columns:
        daily = df.groupby('День')['Сумма заказов (из ленты в API)'].sum()
        st.info(f"🏆 Лучший день: {daily.idxmax()} (Сумма: {daily.max():,.2f} ₽)")

    # 2. Основные метрики (с рублями)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Заказов (шт)", f"{df['Заказы (из ленты в API)'].sum():,}")
    c2.metric("Сумма заказов", f"{df['Сумма заказов (из ленты в API)'].sum():,.2f} ₽")
    c3.metric("Валовая прибыль", f"{df['Валовая выручка'].sum() if 'Валовая выручка' in df.columns else 0:,.2f} ₽")
    c4.metric("Возвраты", f"{df['Возвраты заказов'].sum() if 'Возвраты заказов' in df.columns else 0} шт.")

    # 3. Расходы: Реклама, Склад и Маржа
    st.markdown("---")
    st.header("🛡️ Реклама и Складские расходы")
    a1, a2, a3 = st.columns(3)
    a1.metric("Реклама", f"{abs(df['Продвижение'].sum()) if 'Продвижение' in df.columns else 0:,.2f} ₽")
    a2.metric("Склад", f"{(abs(df['Хранение'].sum()) if 'Хранение' in df.columns else 0) + (abs(df['Платная приемка'].sum()) if 'Платная приемка' in df.columns else 0):,.2f} ₽")
    a3.metric("Маржа", f"{df['Фронт-маржинальность'].mean():.1f}%" if 'Фронт-маржинальность' in df.columns else "N/A")

    # 4. Расходы: Удержания и логистика (с рублями)
    st.markdown("---")
    st.header("💸 Удержания и Базовая Логистика")
    l1, l2, l3 = st.columns(3)
    l1.metric("Штрафы", f"{abs(df['Штрафы'].sum()) if 'Штрафы' in df.columns else 0:,.2f} ₽")
    l2.metric("Логистика", f"{abs(df['Логистика'].sum()) if 'Логистика' in df.columns else 0:,.2f} ₽")
    l3.metric("Эквайринг", f"{abs(df['Эквайринг'].sum()) if 'Эквайринг' in df.columns else 0:,.2f} ₽")

    # 5. ИИ-Агент
    st.markdown("---")
    st.header("🤖 Спросить ИИ-Агента")
    user_query = st.text_input("Введите вопрос о деталях таблицы:")
    
    if user_query:
        with st.spinner("Анализирую данные..."):
            try:
                # Передаем итоги в ИИ
                prompt = f"Вопрос: {user_query}. Данные: Себестоимость {df['Себестоимость'].sum() if 'Себестоимость' in df.columns else 0}, Штрафы {df['Штрафы'].sum() if 'Штрафы' in df.columns else 0}, Логистика {df['Логистика'].sum() if 'Логистика' in df.columns else 0}. Отвечай кратко и с цифрами."
                
                client = Client()
                response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                st.markdown("### 📝 Ответ:")
                st.write(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Ошибка ИИ: {e}")
else:
    st.info("👈 Загрузите отчет на панели слева.")