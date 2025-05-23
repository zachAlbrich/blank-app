import pandas as pd
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")  # Replace or use Streamlit secrets

def match_catalog_to_export(catalog_df, export_df, matching_rules):
    results = []
    matched_export_indices = set()

    for _, cat_row in catalog_df.iterrows():
        match_found = False
        match_type = ""
        match_reason = ""
        matched_export_row = None

        for rule in matching_rules:
            if match_found:
                break
            cat_value = str(cat_row[rule["catalog_col"]]).strip().lower()

            for idx, exp_row in export_df.iterrows():
                exp_value = str(exp_row[rule["export_col"]]).strip().lower()
                if cat_value and cat_value == exp_value:
                    match_found = True
                    match_type = f"Direct - {rule['label']}"
                    match_reason = f"Exact match on {rule['label']}"
                    matched_export_row = exp_row
                    matched_export_indices.add(idx)
                    break

        if not match_found:
            # Semantic matching fallback
            prompt = build_semantic_prompt(cat_row, export_df, matching_rules)
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You're a smart matcher. Match entries based on SKU, model, name, and description."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.3
                )
                result = response.choices[0].message['content'].strip()
                if "Match Found:" in result:
                    match_type = "Semantic"
                    match_reason = result
                else:
                    match_type = "No Match"
                    match_reason = "No close semantic match found"
            except Exception as e:
                match_type = "Error"
                match_reason = str(e)

        result_row = cat_row.to_dict()
        result_row["Match Type"] = match_type
        result_row["Match Reason"] = match_reason
        results.append(result_row)

    return pd.DataFrame(results)

def build_semantic_prompt(cat_row, export_df, rules):
    # Use selected fields from both sides to construct prompt
    fields = [rule["catalog_col"] for rule in rules]
    prompt = "Catalog Item:\n"
    for field in fields:
        prompt += f"{field}: {cat_row[field]}\n"
    prompt += "\nCompare against the following products:\n"
    for _, row in export_df.iterrows():
        entry = ", ".join([f"{rule['export_col']}: {row[rule['export_col']]}" for rule in rules])
        prompt += f"- {entry}\n"
    prompt += "\nWhich product is the best match for the catalog item? Respond with 'Match Found: [brief reason]' or 'No close semantic match found.'"
    return prompt
