import streamlit as st
import pandas as pd
from brain import advanced_lookup, DIRECT_MATCH_COLUMNS, RELEVANT_SEMANTIC_COLUMNS

st.set_page_config(page_title="Semantic Matching Lookup", layout="centered")

st.title("🧠 Semantic Matching Lookup Tool")

uploaded_file = st.file_uploader("📁 Upload your CSV", type=["csv"])
query = st.text_input("🔍 Enter the value you're searching for")

if uploaded_file and query:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("✅ File uploaded successfully!")
        st.write("Preview:", df.head())

        # Perform the advanced lookup
        result = advanced_lookup(query, DIRECT_MATCH_COLUMNS, RELEVANT_SEMANTIC_COLUMNS)

        if result is not None:
            st.success("🎯 Match found:")
            st.write(result)
        else:
            st.warning("No match found.")
    except Exception as e:
        st.error(f"Something went wrong: {e}")
