import streamlit as st
import pandas as pd
import json
import os
from catalog_library import register_catalog, list_registered_catalogs
from brain import match_catalog_to_export

CACHE_FILE = "semantic_match_cache.json"

st.set_page_config(page_title="Catalog Matcher", layout="wide")
st.title("Catalog to Export Matcher")

# --- Catalog File Registration ---
st.sidebar.header("Register a Catalog")
catalog_file = st.sidebar.file_uploader("Upload Catalog CSV", type="csv")
catalog_name_input = st.sidebar.text_input("Name for this Catalog")

if catalog_file and catalog_name_input and st.sidebar.button("Register Catalog"):
    with open("temp_catalog.csv", "wb") as f:
        f.write(catalog_file.getvalue())
    file_id = register_catalog("temp_catalog.csv", catalog_name_input)
    st.sidebar.success(f"Catalog '{catalog_name_input}' registered.")

registered_catalogs = list_registered_catalogs()
selected_catalog = st.sidebar.selectbox("Choose a Registered Catalog", list(registered_catalogs.keys()))

# --- Export File Upload ---
st.sidebar.header("Upload Export File")
export_file = st.sidebar.file_uploader("Upload Export CSV", type="csv")

if export_file:
    export_df = pd.read_csv(export_file)
    st.success("Export file uploaded successfully.")

    # --- Matching Rules Setup ---
    st.sidebar.header("Set Matching Rules")
    st.session_state.setdefault("rules", [])

    with st.sidebar.form("rule_form"):
        if len(export_df.columns) > 0:
            rule_label = st.text_input("Rule Label (e.g., SKU, Name)")
            export_col = st.selectbox("Column from Export File", export_df.columns)
            add_rule = st.form_submit_button("Add Rule")

            if add_rule and rule_label:
                st.session_state.rules.append({
                    "label": rule_label,
                    "export_col": export_col,
                    "catalog_col": rule_label
                })

    if st.session_state.rules:
        st.subheader("Matching Rules")
        for idx, rule in enumerate(st.session_state.rules):
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"{idx+1}. {rule['label']}: '{rule['export_col']}' to '{rule['catalog_col']}'")
            with col2:
                if st.button("Remove", key=f"remove_rule_{idx}"):
                    st.session_state.rules.pop(idx)
                    st.experimental_rerun()

    # --- Matching Execution ---
    if st.button("Run Matching"):
        with st.spinner("Processing matches..."):
            try:
                result_df = match_catalog_to_export(selected_catalog, export_df.copy(), st.session_state.rules)
                st.success("Matching completed.")

                # Filter out very low confidence matches (below 5)
                result_df = result_df[~((result_df["Match Type"] == "Semantic (Low Confidence)") & (result_df["Match Reason"].str.contains("confidence", case=False) & result_df["Match Reason"].str.extract(r'(\d+)').astype(float)[0] < 5))]

                st.subheader("Match Results")
                def flag_low_conf(row):
                    if row["Match Type"] == "Semantic (Low Confidence)":
                        return "⚠️ Low Confidence"
                    return ""
                result_df["Flag"] = result_df.apply(flag_low_conf, axis=1)
                st.dataframe(result_df, use_container_width=True)

                st.download_button(
                    label="Download All Matches as CSV",
                    data=result_df.to_csv(index=False).encode("utf-8"),
                    file_name="match_results.csv",
                    mime="text/csv",
                )
            except Exception as e:
                st.error(f"An error occurred: {e}")

    # --- View Cache Content ---
    st.sidebar.header("Match Cache Management")
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache_data = json.load(f)
        if st.sidebar.button("Clear Match Cache"):
            os.remove(CACHE_FILE)
            st.sidebar.success("Match cache cleared.")
        else:
            st.sidebar.markdown(f"Current cache contains {len(cache_data)} entries.")
            if st.sidebar.checkbox("Show Cache Preview"):
                st.json(cache_data)
else:
    st.info("Upload an export file to get started.")