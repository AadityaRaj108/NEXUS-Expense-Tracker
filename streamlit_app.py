import streamlit as st
from app import create_app

st.set_page_config(page_title="NEXUS Expense Tracker", page_icon="◈", layout="wide")

st.markdown("""
<style>
.stApp{background:#070912;color:#f4f6ff}
[data-testid="stSidebar"]{background:#090c17}
h1,h2,h3{letter-spacing:1px}
</style>
""", unsafe_allow_html=True)

st.title("◈ NEXUS")
st.caption("Intelligent Personal Finance Command Center")

flask_app = create_app()

st.success("NEXUS application backend initialized successfully.")

st.info(
    "The Streamlit deployment is connected to the NEXUS Flask application. "
    "The original Flask interface remains preserved."
)

st.subheader("Deployment Status")
c1,c2,c3=st.columns(3)
c1.metric("Application","NEXUS")
c2.metric("Backend","Flask")
c3.metric("Deployment","Streamlit")

