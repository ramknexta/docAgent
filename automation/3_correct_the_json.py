import re
import json
from pathlib import Path

def clean_raw_response(text: str) -> str:
    """Remove markdown fences like ```json and extra formatting."""
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").strip()
    return cleaned


# ---------------------------------------------------
# 📂 Define Input & Output Folders (Absolute Paths)
# ---------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]  # project root
input_folder = BASE_DIR / "json_output"
output_folder = BASE_DIR / "json_corrected"
output_folder.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------
# 🧹 Process and Clean Each JSON File
# ---------------------------------------------------
for json_file in input_folder.glob("*.json"):
    print(f"🧾 Processing: {json_file.name}")

    # Load JSON data
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    corrected_data = {}

    # Go through each entry inside the JSON file
    for file_name, content in data.items():
        if isinstance(content, dict) and "raw_response" in content:
            raw_text = content["raw_response"]
            cleaned_text = clean_raw_response(raw_text)

            # Try to convert cleaned string into valid JSON
            try:
                corrected_json = json.loads(cleaned_text)
                corrected_data[file_name] = corrected_json
            except json.JSONDecodeError:
                print(f"⚠️ Invalid JSON in {file_name}, keeping as raw text")
                corrected_data[file_name] = {"raw_response": cleaned_text}
        else:
            # If already valid structured JSON, copy as is
            corrected_data[file_name] = content

    # Save cleaned data
    output_path = output_folder / json_file.name
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(corrected_data, f, indent=4, ensure_ascii=False)

    print(f"✅ Saved corrected JSON → {output_path}\n")

print("🎯 All JSON files cleaned and saved in './json_corrected/'")
