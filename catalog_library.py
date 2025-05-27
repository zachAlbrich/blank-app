import openai
import os
import json

openai.api_key = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
CATALOG_FILE_MAP = "catalog_files.json"

def register_catalog(file_path: str, catalog_name: str) -> str:
    """
    Uploads a catalog CSV to OpenAI File API and stores its mapping to a friendly name.
    Returns the file ID.
    """
    file = openai.files.create(file=open(file_path, "rb"), purpose="assistants")
    mapping = load_catalog_file_map()
    mapping[catalog_name] = file.id
    save_catalog_file_map(mapping)
    return file.id

def get_catalog_file_id(catalog_name: str) -> str:
    """
    Retrieves the OpenAI file ID for a given catalog name.
    """
    mapping = load_catalog_file_map()
    return mapping.get(catalog_name)

def list_registered_catalogs() -> dict:
    """
    Returns the mapping of all registered catalog names to file IDs.
    """
    return load_catalog_file_map()

def load_catalog_file_map() -> dict:
    if os.path.exists(CATALOG_FILE_MAP):
        with open(CATALOG_FILE_MAP, "r") as f:
            return json.load(f)
    return {}

def save_catalog_file_map(mapping: dict):
    with open(CATALOG_FILE_MAP, "w") as f:
        json.dump(mapping, f, indent=2)
