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

    # --- Filter Export File ---
    st.sidebar.header("Step 2: Filter Export Data")
    sheet_selection = st.sidebar.radio("Filter which file?", ["Export", "Catalog"])
    selected_df = export_df if sheet_selection == "Export" else catalog_df

    filter_column = st.sidebar.selectbox("Select column to filter", selected_df.columns)
    filter_unique_values = selected_df[filter_column].dropna().unique().tolist()
    filter_operator = st.sidebar.selectbox("Filter condition", ["Equals", "Does Not Equal", "Greater Than", "Less Than", "Is Empty", "Is Not Empty"])
    filter_value = st.sidebar.selectbox("Select filter value", filter_unique_values) if filter_operator not in ["Is Empty", "Is Not Empty"] else None

    if filter_column:
        if filter_operator == "Equals":
            selected_df = selected_df[selected_df[filter_column] == filter_value]
        elif filter_operator == "Does Not Equal":
            selected_df = selected_df[selected_df[filter_column] != filter_value]
        elif filter_operator == "Greater Than":
            selected_df = selected_df[pd.to_numeric(selected_df[filter_column], errors='coerce') > pd.to_numeric(filter_value, errors='coerce')]
        elif filter_operator == "Less Than":
            selected_df = selected_df[pd.to_numeric(selected_df[filter_column], errors='coerce') < pd.to_numeric(filter_value, errors='coerce')]
        elif filter_operator == "Is Empty":
            selected_df = selected_df[selected_df[filter_column].isna() | (selected_df[filter_column] == "")]
        elif filter_operator == "Is Not Empty":
            selected_df = selected_df[selected_df[filter_column].notna() & (selected_df[filter_column] != "")]

        if sheet_selection == "Export":
            export_df = selected_df
        else:
            catalog_df = selected_df

    # --- Column Selection ---
    st.sidebar.header("Step 3: Add Matching Rules")
    st.session_state.setdefault("rules", [])

    with st.sidebar.form("add_rule_form"):
        rule_label = st.text_input("Rule Label (e.g. SKU, Name, Model Number)")
        catalog_col = st.selectbox("Select Catalog Column", catalog_df.columns, key="catalog_col")
        export_col = st.selectbox("Select Export Column", export_df.columns, key="export_col")
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
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"**{idx+1}.** {rule['label']}: `{rule['catalog_col']}` → `{rule['export_col']}`")
            with col2:
                if st.button("❌", key=f"delete_rule_{idx}"):
                    st.session_state.rules.pop(idx)
                    st.experimental_rerun()

    # --- Column Replacement ---
    st.sidebar.header("Step 4: Select Replacement Columns")
    st.session_state.setdefault("replace_columns", [])

    with st.sidebar.form("replace_columns_form"):
        replacement_catalog_col = st.selectbox("Select Catalog Column to Replace From", catalog_df.columns)
        replacement_export_col = st.selectbox("Select Export Column to Replace Into", export_df.columns)
        add_replacement = st.form_submit_button("Add Replacement Rule")

    if add_replacement:
        st.session_state.replace_columns.append({
            "from": replacement_catalog_col,
            "to": replacement_export_col
        })

    if st.session_state.replace_columns:
        st.subheader("🔄 Replacement Rules")
        for idx, rule in enumerate(st.session_state.replace_columns):
            st.markdown(f"**{idx+1}.** Replace `{rule['to']}` with `{rule['from']}`")

    # --- Run Matching and Replacement ---
    if st.button("🔍 Run Matching and Replacement"):
        with st.spinner("Matching in progress..."):
            result_df = match_catalog_to_export(
                catalog_df,
                export_df.copy(),  # Keep original export_df intact
                st.session_state.rules
            )

            # Display how the match happened
            st.subheader("📌 Match Summary")
            if "Match Type" in result_df.columns:
                match_summary = result_df["Match Type"].value_counts()
                st.write("### Match Types Summary")
                st.dataframe(match_summary)

            # Split matched and unmatched
            matched_df = result_df[result_df["Match Type"] != "No Match"]
            unmatched_df = result_df[result_df["Match Type"] == "No Match"]

            # Show unmatched summary
            st.markdown(f"#### Export ({len(unmatched_df)}) unmatched items")

            # Merge results for matched detail display
            display_df = result_df.copy()
            if "Match Type" in display_df.columns:
                display_df["Match Summary"] = display_df["Match Type"]

            # Apply replacements to export_df
            for idx, row in result_df.iterrows():
                if row.get("Match Type") not in ["No Match", "Error"]:
                    for rule in st.session_state.rules:
                        match_row = export_df[export_df[rule["export_col"]] == row[rule["catalog_col"]]]
                        if not match_row.empty:
                            match_index = match_row.index[0]
                            export_df.loc[match_index, "Match Type"] = row["Match Type"]  # Add match type to export
                            export_df.loc[match_index, "Match Reason"] = row.get("Match Reason", "")
                            for rep_rule in st.session_state.replace_columns:
                                export_df.at[match_index, rep_rule["to"]] = row[rep_rule["from"]]

        st.success("✅ Matching and Replacement complete!")
        st.subheader("📋 Updated Export Table")
        st.dataframe(export_df)

        csv = export_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📅 Download Updated Export as CSV",
            data=csv,
            file_name="updated_export.csv",
            mime="text/csv",
        )

        if not unmatched_df.empty:
            unmatched_csv = unmatched_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="🔹 Download Unmatched Items as CSV",
                data=unmatched_csv,
                file_name="unmatched_items.csv",
                mime="text/csv",
            )
else:
    st.info("👈 Upload both files to get started.")