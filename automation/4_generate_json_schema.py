import os
import json
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# -----------------------------
# Load Gemini API key
# -----------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GENIE_API_KEY"))

# -----------------------------
# Function: Generate JSON Schema
# -----------------------------
def generate_json_schema_from_form(html_file_path: str, output_json: str = None):
    """
    Uses Gemini LLM to read a given HTML form and generate a structured JSON schema.
    """

    # Convert to Path object
    html_path = Path(html_file_path).resolve()

    if not html_path.exists():
        raise FileNotFoundError(f"❌ HTML form not found at: {html_path}")

    # Read HTML content
    html_content = html_path.read_text(encoding="utf-8")

    # Prepare output path
    if output_json is None:
        output_json = html_path.stem + "_schema.json"

    # Ensure schemas directory exists
    output_dir = Path(__file__).resolve().parent.parent / "schema"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / output_json

    # Prompt for Gemini
    prompt = f"""
You are an AI that generates structured JSON schemas from HTML forms.

Here is an HTML form used for collecting Home Loan information.

Your task:
- Analyze the <form> structure and its inputs.
- Create a JSON schema representing the logical data model.
- Group related inputs (e.g., identity_proof, address_proof, etc.)
- Include empty string values for fields that accept text input.
- Use nested JSON for grouped form sections (e.g., KYC, Income, Property Documents).
- Output only the JSON — no explanations.

HTML Form:
{html_content}
"""

    # Generate schema using Gemini
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    raw_output = response.text.strip()

    # Clean markdown code block if present
    if raw_output.startswith("```"):
        raw_output = raw_output.split("```json")[-1].split("```")[0].strip()

    # Parse JSON safely
    try:
        schema = json.loads(raw_output)
    except json.JSONDecodeError:
        print("⚠️ Gemini output is not a valid JSON. Saving raw output instead.")
        schema = {"raw_response": raw_output}

    # Save schema to file
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(schema, file, indent=4, ensure_ascii=False)

    print(f"✅ JSON schema generated and saved successfully at: {output_path}")
    return schema


# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent  # project root
    form_path = BASE_DIR / "forms" / "form.html"  # ✅ correct form path
    generate_json_schema_from_form(form_path)
