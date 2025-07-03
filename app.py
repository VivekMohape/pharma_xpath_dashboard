import streamlit as st
from lxml import html
import os
from utils import (
    clean_html_for_llm,
    generate_selectors,
    extract_values_from_html,
    configure_langsmith_tracing
)

st.set_page_config(page_title="Pharma XPath Validator", layout="wide")
st.title(" Pharma News Parser Validator")

# Only OpenAI key input
openai_key = st.text_input(" Enter your OpenAI API Key", type="password")

if not openai_key:
    st.warning("Please enter your OpenAI API key to continue.")
    st.stop()

# LangSmith is configured using ENV
configure_langsmith_tracing()

# Load HTML
html_dir = "html"
html_files = sorted([f for f in os.listdir(html_dir) if f.endswith(".html")])
selected_file = st.selectbox("🗂 Select HTML File", html_files)
file_path = os.path.join(html_dir, selected_file)

with open(file_path, "r", encoding="utf-8") as f:
    raw_html = f.read()

cleaned = clean_html_for_llm(raw_html)
selectors = generate_selectors(cleaned, openai_key)
extracted = extract_values_from_html(raw_html, selectors)

# Layout
col1, col2 = st.columns(2)

with col1:
    st.subheader(" Raw HTML (Truncated)")
    st.code(raw_html[:5000], language="html")

with col2:
    st.subheader(" Extracted Output")
    st.markdown(f"** Title:** {extracted['title']}")
    st.markdown(f"** Date:** {extracted['date']}")
    st.markdown("** Content Preview:**")
    st.text_area("Full Content", value=extracted["content"], height=400, disabled=True)

# Editable Selectors
with st.expander(" XPath Selectors (Editable)"):
    title_sel = st.text_input("Title Selector", selectors.title_selector)
    date_sel = st.text_input("Date Selector", selectors.date_selector)
    content_sel = st.text_area("Content Selector", selectors.content_selector)
    save = st.button(" Approve and Save")
    if save:
        st.success(" Selectors approved and saved (not implemented yet).")
