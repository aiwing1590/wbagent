import streamlit as st
import pandas as pd

# Настройка страницы
st.set_page_config(page_title="WB AI Agent Analyzer", layout="wide")

# ================= ЗАЩИТА ПАРОЛЕМ =================
def check_password():
    def password_entered():
        if st.session_state.get("username") == "ceoprof" and st.session_state.get("password") == "wb140":
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
    st.success("Данные загружены!")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Заказов (шт)", f"{df['Заказы (из ленты в API)'].sum():,}")
    c2.metric("Сумма заказов", f"{df['Сумма заказов (из ленты в API)'].sum():,.2f} ₽")
    c3.metric("Валовая прибыль", f"{df['Валовая выручка'].sum() if 'Валовая выручка' in df.columns else 0:,.2f} ₽")
    c4.metric("Возвраты", f"{df['Возвраты заказов'].sum() if 'Возвраты заказов' in df.columns else 0} шт.")

    st.markdown("---")
    st.info("💡 Аналитическая часть работает. Раздел с ИИ временно отключен из-за ограничений сервера.")
else:
    st.info("👈 Загрузите отчет на панели слева.")
