import pandas as pd
import openai
import os
import time
import json
import hashlib
from catalog_library import get_catalog_file_id

openai.api_key = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
ASSISTANT_ID = "asst_iRof5BkKLvS8EVBEf2PExzgy"
CACHE_FILE = "semantic_match_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def get_cache_key(export_row, catalog_name):
    raw = json.dumps(export_row.to_dict(), sort_keys=True) + catalog_name
    return hashlib.md5(raw.encode()).hexdigest()

def match_catalog_to_export(catalog_name, export_df, matching_rules):
    results = []
    catalog_file_id = get_catalog_file_id(catalog_name)
    if not catalog_file_id:
        raise ValueError(f"Catalog '{catalog_name}' not found in registered catalogs.")

    cache = load_cache()

    for idx, exp_row in export_df.iterrows():
        match_type = "No Match"
        match_reason = ""
        matched_index = None

        # --- Prefilter: Skip empty or incomplete rows ---
        if not exp_row.dropna().any():
            continue
        if "sku" in exp_row and pd.isna(exp_row["sku"]):
            continue

        cache_key = get_cache_key(exp_row, catalog_name)
        if cache_key in cache:
            cached = cache[cache_key]
            match_type = cached["Match Type"]
            match_reason = cached["Match Reason"]
            matched_index = cached["Matched Catalog Index"]
        else:
            try:
                prompt = build_semantic_prompt(exp_row, catalog_name)
                thread = openai.beta.threads.create()
                openai.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=prompt,
                    file_ids=[catalog_file_id]
                )
                run = openai.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=ASSISTANT_ID
                )

                while True:
                    run_status = openai.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )
                    if run_status.status in ["completed", "failed"]:
                        break
                    time.sleep(1)

                if run_status.status == "completed":
                    messages = openai.beta.threads.messages.list(thread_id=thread.id)
                    reply = messages.data[0].content[0].text.value.strip()
                    try:
                        parsed = json.loads(reply)
                        confidence = parsed.get("confidence", 0)
                        if parsed.get("match_found") and confidence >= 7:
                            match_type = "Semantic"
                            match_reason = parsed.get("reason", "")
                            matched_index = parsed.get("catalog_index")
                        elif confidence >= 4:
                            match_type = "Semantic (Low Confidence)"
                            match_reason = parsed.get("reason", "")
                    except json.JSONDecodeError:
                        match_reason = f"Could not parse response: {reply}"
            except Exception as e:
                match_type = "Error"
                match_reason = str(e)

            # Save to cache
            cache[cache_key] = {
                "Match Type": match_type,
                "Match Reason": match_reason,
                "Matched Catalog Index": matched_index
            }

        result_row = exp_row.to_dict()
        result_row["Match Type"] = match_type
        result_row["Match Reason"] = match_reason
        result_row["Matched Catalog Index"] = matched_index
        results.append(result_row)

    save_cache(cache)
    return pd.DataFrame(results)

def build_semantic_prompt(export_row, catalog_name):
    return (
        f"You are a funeral home product expert. Match the following export item to one product in the catalog named '{catalog_name}', which is provided as a file.\n"
        f"Return a JSON with keys: match_found (bool), catalog_index (int, optional), reason (str), confidence (1-10).\n"
        f"Only match items that are clearly the same product, using SKU similarity, product name alignment, and description match.\n"
        f"Do not match unrelated items like 'Keepsake' and 'Urn'.\n"
        f"Reject any match where information is inconsistent or contradictory.\n\n"
        f"Export Item:\n{json.dumps(export_row.to_dict(), indent=2)}"
    )