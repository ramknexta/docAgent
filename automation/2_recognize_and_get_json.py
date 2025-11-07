import os
import json
import fitz  # PyMuPDF for PDFs
import pytesseract
from pathlib import Path
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

# Load API key
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 🔹 Base Directories
BASE_DIR = Path(__file__).resolve().parents[1] / "organized_docs" / "Home Loan"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "json_output"

# Folder names under "Home Loan"
FOLDERS = ["KYC Docs", "Income Docs", "Property Docs"]

# Create output directory if not exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 🔹 (Optional) Configure Tesseract path if needed
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# -------------------------------------------------
# 🧠 Function: Extract text from image or PDF
# -------------------------------------------------
def extract_text(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    text = ""
    try:
        if ext in [".jpg", ".jpeg", ".png"]:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang="eng")
        elif ext == ".pdf":
            with fitz.open(file_path) as pdf:
                for page in pdf:
                    text += page.get_text("text") + "\n"
    except Exception as e:
        print(f"⚠️ Error reading {file_path.name}: {e}")
    return text.strip()


# -------------------------------------------------
# 🤖 Function: Analyze with Gemini LLM
# -------------------------------------------------
def analyze_with_llm(extracted_text: str, file_name: str, folder_type: str) -> dict:
    prompt = f"""
    You are an expert document analyzer and data extractor.
    You are given text extracted from a scanned document.
    Based on the folder type "{folder_type}", convert the extracted text into a structured JSON.

    Your task:
    1. Identify details like names, addresses, IDs (Aadhaar, PAN, registration numbers), dates, amounts, companies, bank details, etc.
    2. Output a **strictly valid JSON** (no markdown, no explanation).
    3. Ensure hierarchical grouping where needed, with clear keys (e.g., name, aadhaar_number, address, date, etc.).

    Document Text:
    \"\"\"{extracted_text}\"\"\"
    """

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)

    try:
        data = json.loads(response.text)
    except json.JSONDecodeError:
        data = {"raw_response": response.text}
    return data


# -------------------------------------------------
# ⚙️ Function: Process all documents
# -------------------------------------------------
def process_documents():
    for folder_name in FOLDERS:
        folder_path = BASE_DIR / folder_name
        print(f"\n📂 Processing folder: {folder_name}")

        if not folder_path.exists():
            print(f"⚠️ Folder not found: {folder_path}")
            continue

        folder_data = {}

        for file_path in folder_path.iterdir():
            if not file_path.is_file():
                continue

            print(f"🔍 Reading: {file_path.name}")
            text = extract_text(file_path)

            if not text:
                print(f"⚠️ No text found in {file_path.name}")
                continue

            structured_data = analyze_with_llm(text, file_path.name, folder_name)
            folder_data[file_path.name] = structured_data

        # Save JSON for this folder in json_output
        output_json_path = OUTPUT_DIR / f"{folder_name.replace(' ', '_')}.json"
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(folder_data, f, indent=4, ensure_ascii=False)

        print(f"✅ JSON saved to: {output_json_path}\n")


# -------------------------------------------------
# 🚀 Run the process
# -------------------------------------------------
if __name__ == "__main__":
    process_documents()
