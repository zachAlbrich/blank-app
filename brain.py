# Install necessary libraries
!pip install gspread oauth2client pandas openai

import gspread
from google.colab import auth
from oauth2client.client import GoogleCredentials
import pandas as pd
import openai
import os
import os
openai.api_key = os.getenv("OPENAI_API_KEY")

# Authenticate Colab for Google Sheets access
auth.authenticate_user()
gc = gspread.authorize(GoogleCredentials.get_application_default())

# --- Configuration ---
# Replace with your Google Sheet link or key
# You can find the key in the URL: https://docs.google.com/spreadsheets/d/YOUR_SHEET_KEY/edit
SPREADSHEET_KEY = 'YOUR_SHEET_KEY'
SHEET_NAME = 'Sheet1' # Replace with the name of your sheet

# Columns to search for direct matches
DIRECT_MATCH_COLUMNS = ['Column1', 'Column2', 'Column3'] # Replace with your column names

# Set your OpenAI API key as an environment variable
# Or replace 'YOUR_OPENAI_API_KEY' with your actual key
# It's recommended to use environment variables for security
# !echo "export OPENAI_API_KEY='YOUR_OPENAI_API_KEY'" >> ~/.bashrc
# !source ~/.bashrc
# openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = 'YOUR_OPENAI_API_KEY' # Replace with your actual key

# --- Function to load data from Google Sheet ---
def load_data_from_sheet(spreadsheet_key, sheet_name):
    """Loads data from a Google Sheet into a pandas DataFrame."""
    try:
        spreadsheet = gc.open_by_key(spreadsheet_key)
        worksheet = spreadsheet.worksheet(sheet_name)
        # Get all values as a list of lists
        data = worksheet.get_all_values()
        # Convert to DataFrame, using the first row as headers
        df = pd.DataFrame(data[1:], columns=data[0])
        return df
    except Exception as e:
        print(f"Error loading data from Google Sheet: {e}")
        return None

# --- Function for Direct Matching ---
def find_direct_match(df, query, columns):
    """Searches for a direct match of the query in specified columns."""
    for col in columns:
        # Ensure the column exists and is not empty
        if col in df.columns and not df[col].empty:
            # Use .str.contains for substring matching or == for exact match
            # Let's use == for exact match as per XLOOKUP
            match = df[df[col] == query]
            if not match.empty:
                # Return the first matching row
                return match.iloc[0]
    return None

# --- Function for Semantic Matching using an LLM ---
def find_semantic_match(df, query, relevant_columns):
    """Finds a semantic match for the query using an LLM."""
    if not openai.api_key:
        print("OpenAI API key is not set. Cannot perform semantic matching.")
        return None

    # Prepare the data for the LLM prompt
    # We'll provide a few examples from the dataframe for context
    sample_data = df[relevant_columns].head(5).to_string(index=False)

    prompt = f"""
    You are a highly accurate data matcher. Given a query and a list of entries, identify the entry that is semantically closest to the query.
    Prioritize strong semantic similarity. If no entry is closely related, indicate that.

    Query: "{query}"

    Data entries (example format):
    {sample_data}
    ... (rest of the data is implicit)

    Consider the following full dataset (only showing a small example above).

    Which entry in the dataset (considering all relevant columns {relevant_columns}) is the best semantic match for the query "{query}"?
    Respond with the primary identifier of the matched row (e.g., a unique ID or the value from a key column if you have one), or "No close semantic match found".
    If you find a match, please also briefly explain why it's a good match.
    Format your response clearly.

    Example Good Match Response:
    Match Found: [Primary Identifier]
    Reason: [Brief explanation]

    Example No Match Response:
    No close semantic match found.
    """

    try:
        # Use the Chat Completions API
        response = openai.ChatCompletion.create(
          model="gpt-3.5-turbo", # Or "gpt-4" for potentially better results
          messages=[
              {"role": "system", "content": "You are a helpful assistant that identifies semantic matches in data."},
              {"role": "user", "content": prompt}
          ],
          max_tokens=150,
          n=1,
          stop=None,
          temperature=0.5, # Adjust temperature for creativity/determinism
        )
        llm_response_text = response.choices[0].message['content'].strip()

        # Parse the LLM response
        if "Match Found:" in llm_response_text:
            # Extract the identifier. This parsing might need refinement based on your actual LLM output format.
            match_identifier_line = [line for line in llm_response_text.split('\n') if "Match Found:" in line]
            if match_identifier_line:
                match_identifier = match_identifier_line[0].replace("Match Found:", "").strip()

                # Now, search the DataFrame for this identifier.
                # You need to replace 'PRIMARY_IDENTIFIER_COLUMN' with the actual column name
                # that contains the unique identifiers the LLM is expected to return.
                PRIMARY_IDENTIFIER_COLUMN = 'Your_Primary_ID_Column' # <<<<<<< IMPORTANT: REPLACE THIS

                if PRIMARY_IDENTIFIER_COLUMN in df.columns:
                    semantic_match_row = df[df[PRIMARY_IDENTIFIER_COLUMN].astype(str) == match_identifier]
                    if not semantic_match_row.empty:
                         # Return the first matching row found by identifier
                        return semantic_match_row.iloc[0]
                    else:
                        print(f"LLM suggested identifier '{match_identifier}' but could not find it in the DataFrame.")
                        return None
                else:
                     print(f"Primary identifier column '{PRIMARY_IDENTIFIER_COLUMN}' not found in DataFrame. Cannot locate LLM match.")
                     return None

        else:
            print("LLM response indicates no close semantic match found.")
            return None

    except Exception as e:
        print(f"Error during semantic matching with LLM: {e}")
        return None

# --- Main function to perform the lookup ---
def advanced_lookup(query, direct_match_columns, relevant_semantic_columns):
    """
    Performs a lookup prioritizing direct matches, then falling back to semantic matching.

    Args:
        query (str): The value to search for.
        direct_match_columns (list): List of column names for direct matching.
        relevant_semantic_columns (list): List of column names containing data
                                           relevant for semantic comparison (for the LLM).

    Returns:
        pandas.Series or None: The matched row as a pandas Series, or None if no match found.
    """
    df = load_data_from_sheet(SPREADSHEET_KEY, SHEET_NAME)
    if df is None:
        return None # Could not load data

    print(f"Attempting direct match for query: '{query}'")
    direct_match = find_direct_match(df, query, direct_match_columns)

    if direct_match is not None:
        print("Direct match found!")
        return direct_match
    else:
        print("No direct match found. Attempting semantic match...")
        semantic_match = find_semantic_match(df, query, relevant_semantic_columns)
        if semantic_match is not None:
            print("Semantic match found!")
            return semantic_match
        else:
            print("No direct or semantic match found.")
            return None

# --- How to use the function ---
# Replace 'Your_Relevant_Semantic_Columns' with the columns
# that contain the text the LLM should use for semantic comparison.
# These might be the same as or different from DIRECT_MATCH_COLUMNS.
RELEVANT_SEMANTIC_COLUMNS = ['Column1', 'Column2', 'Column3', 'Description_Column'] # Example

# Example Usage:
# query_to_find = "Value I want to look up"
# result_row = advanced_lookup(query_to_find, DIRECT_MATCH_COLUMNS, RELEVANT_SEMANTIC_COLUMNS)

# if result_row is not None:
#     print("\nLookup Result:")
#     print(result_row)
# else:
#     print("\nLookup failed: No match found.")
