"""Service Desk AI агент — Streamlit апп. Ажиллуулах: streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="Service Desk AI агент", page_icon="🛟", layout="wide")

nav = st.navigation([
    st.Page("views/chat.py", title="Агент турших", icon="💬", default=True),
    st.Page("views/tickets.py", title="Тикетүүд", icon="🎫"),
    st.Page("views/test_suite.py", title="Тест (20 мессеж)", icon="🧪"),
    st.Page("views/admin.py", title="Хяналт (Admin)", icon="🛡️"),
])
nav.run()
