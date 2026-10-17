import streamlit as st

RTL_CSS = """
<style>
@font-face { font-family: 'LocalArabic'; src: local('Tahoma'); }
html, body, [class*="css"], .stApp { direction: rtl; text-align: right; }
[data-testid="stSidebar"] { direction: rtl; }
[data-testid="stSidebar"] * { text-align: right; }
.stButton button, .stTextInput input, .stSelectbox div, .stTextArea textarea { direction: rtl; }
.block-container { padding-top: 1.4rem; max-width: 1200px; }
.cmms-card { border: 1px solid #d9dee7; border-radius: 14px; padding: 14px 16px; margin-bottom: 10px; }
.cmms-muted { color: #657080; font-size: .9rem; }
</style>
"""
def apply_theme(): st.markdown(RTL_CSS, unsafe_allow_html=True)
