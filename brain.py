import pandas as pd
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

def match_catalog_to_export(catalog_df, export_df, matching_rules):
    results = []
    matched_export_indices = set()

    for _, cat_row in catalog_df.iterrows():
        match_found = False
        match_type = "No Match"
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
            prompt = build_semantic_prompt(cat_row, export_df, matching_rules)

            # DEBUG: log prompt to console
            print("\n🧠 SEMANTIC MATCH PROMPT:\n" + prompt + "\n")

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": (
                            "You are a funeral home expert, matching information using details from two different spreadsheets of funeral home products, goods, services etc. "
                            "Your primary function is to accurately parse and match rows from these two sheets based on signifiers such as SKU or item numbers, product names, descriptions, etc. "
                            "using your knowledge as a funeral home expert to make the best assumptions possible such as linking matches like these: "
                            "ID: 1234, Name: Patriot Urn, Description: BLUE and SKU: 1234-BLUE, Product Name: Patriotic URN, Description: an urn to carry your loved ones. "
                            "If match quality is poor or overreaching, flag it as low match quality. Never match unlike items such as 'Keepsake' and 'Urn'."
                        )},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=700,
                    temperature=0.3
                )
                result = response.choices[0].message['content'].strip()
                print("\n🧠 SEMANTIC MATCH RESPONSE:\n" + result + "\n")  # Log response

                if result.lower().startswith("match found:"):
                    match_type = "Semantic"
                    match_reason = result
                elif result.lower().startswith("low match confidence"):
                    match_type = "Semantic (Low Confidence)"
                    match_reason = result
                else:
                    match_type = "No Match"
                    match_reason = result
            except Exception as e:
                match_type = "Error"
                match_reason = str(e)

        result_row = cat_row.to_dict()
        result_row["Match Type"] = match_type
        result_row["Match Reason"] = match_reason
        result_row["Matched Export Index"] = matched_export_row.name if matched_export_row is not None else None
        results.append(result_row)

    return pd.DataFrame(results)

def build_semantic_prompt(cat_row, export_df, rules):
    prompt = "You will receive a catalog item and a list of export products. Compare each and identify the most semantically similar product.\n\nCatalog Item Details:\n"
    for rule in rules:
        catalog_value = cat_row[rule["catalog_col"]]
        prompt += f"{rule['label']} ({rule['catalog_col']}): {catalog_value}\n"

    prompt += "\nExport Product Options:\n"
    for i, row in export_df.iterrows():
        prompt += f"Option {i+1}:\n"
        for rule in rules:
            export_value = row[rule["export_col"]]
            prompt += f"  {rule['label']} ({rule['export_col']}): {export_value}\n"

    prompt += ("\nInstructions:\n"
               "1. Identify if any export item is a strong semantic match based on similarities in SKU, model, name, and description.\n"
               "2. If a SKU and name split into parts match a composed or partial field from another row, consider that a strong indicator.\n"
               "3. If a match is strong, respond with:\nMatch Found: [Option #] - [Brief Reason]\n"
               "4. If no match is appropriate, respond with:\nNo close semantic match found.\n"
               "5. If the match is weak or unclear, respond with:\nLow Match Confidence: [Option #] - [Brief Reason]\n")

    return prompt
