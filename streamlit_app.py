import streamlit as st
import pandas as pd
from brain import match_catalog_to_export

st.set_page_config(page_title="Catalog Matcher", layout="wide")

st.title("📦 Catalog vs Export Matcher")

# --- File Upload ---
st.sidebar.header("Step 1: Upload Files")
catalog_file = st.sidebar.file_uploader("Upload Catalog CSV", type="csv")
export_file = st.sidebar.file_uploader("Upload Product Export CSV", type="csv")

if catalog_file and export_file:
    catalog_df = pd.read_csv(catalog_file)
    export_df = pd.read_csv(export_file)

    st.success("✅ Files uploaded successfully!")

    # --- Column Selection ---
    st.sidebar.header("Step 2: Add Matching Rules")
    st.session_state.setdefault("rules", [])

    with st.sidebar.form("add_rule_form"):
        rule_label = st.text_input("Rule Label (e.g. SKU, Name, Model Number)")
        catalog_col = st.selectbox("Select Catalog Column", catalog_df.columns)
        export_col = st.selectbox("Select Export Column", export_df.columns)
        add_rule = st.form_submit_button("Add Rule")

    if add_rule and rule_label:
        st.session_state.rules.append({
            "label": rule_label,
            "catalog_col": catalog_col,
            "export_col": export_col
        })

    if st.session_state.rules:
        st.subheader("🧠 Matching Rules")
        for idx, rule in enumerate(st.session_state.rules):
            st.markdown(f"**{idx+1}.** {rule['label']}: `{rule['catalog_col']}` → `{rule['export_col']}`")

    # --- Run Matching ---
    if st.button("🔍 Run Matching"):
        with st.spinner("Matching in progress..."):
            result_df = match_catalog_to_export(
                catalog_df,
                export_df,
                st.session_state.rules
            )
        st.success("✅ Matching complete!")
        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name="matched_results.csv",
            mime="text/csv",
        )
else:
    st.info("👈 Upload both files to get started.")
