import os
import re
import shutil
from pathlib import Path
import fitz  # PyMuPDF
import mimetypes
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

# ------------------- CONFIG -------------------
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

# Loan Product Hierarchy
PRODUCT_DOCS = {
    "Home Loan": ["KYC Docs", "Income Docs", "Property Docs"],
    "Small Ticket Home Loan": ["KYC Docs", "Income Docs", "Property Docs"],
    "Home Improvement Loans": ["KYC Docs", "Income Docs", "Property Docs"],
    "Small Ticket Business Loan": ["KYC Docs", "Income Docs", "Business Proof"],
    "Loan Against Property": ["KYC Docs", "Income Docs", "Property Docs"]
}

# Document categories
KYC_DOCS = {
    "IDENTITY_PROOF": [
        "voter id", "passport", "driving license", "pan card", "employee id"
    ],
    "ADDRESS_PROOF": [
        "passport", "ration card", "voter id", "employee id",
        "driving license", "telephone bill", "gas bill", "aadhaar", "aadhar card"
    ],
    "AGE_PROOF": [
        "school leaving certificate", "passport", "driving license", "voter id",
        "birth certificate", "lic policy", "pan card", "aadhaar", "aadhar card"
    ]
}

INCOME_DOCS = [
    "salary slip", "form 16", "bank statement", "income tax return", "payslip"
]

PROPERTY_DOCS = [
    "sale deed", "agreement", "property tax", "electricity bill", "possession letter", "allotment letter"
]

BUSINESS_PROOF = [
    "gst certificate", "shop act license", "partnership deed", "udhyam registration"
]


# ------------------- OCR/LLM HELPERS -------------------
def pdf_to_image(pdf_path: str) -> bytes:
    """Convert first page of PDF to PNG image bytes."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img_bytes = pix.tobytes("png")
    doc.close()
    return img_bytes


def recognize_document(file_path: str) -> str:
    """Use Gemini Vision model to classify the document type."""
    ext = os.path.splitext(file_path)[1].lower()
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = "image/jpeg"

    if ext == ".pdf":
        image_bytes = pdf_to_image(file_path)
        file_data = {"mime_type": "image/png", "data": image_bytes}
    else:
        with open(file_path, "rb") as f:
            file_data = {"mime_type": mime_type, "data": f.read()}

    prompt = """
    You are an AI document classifier for Indian loan applications.
    Identify which document this is (e.g., Aadhaar Card, PAN Card, Driving License, Salary Slip, etc.)
    Respond strictly in lowercase JSON format:
    {"document_type": "<type>"}
    """

    try:
        response = model.generate_content([prompt, file_data])
        result = response.text.strip()
    except Exception as e:
        print(f"⚠️ LLM Error for {file_path}: {e}")
        result = '{"document_type": "unknown"}'

    return result


def sanitize_filename(name: str) -> str:
    """Make safe filename."""
    name = name.lower().replace(" ", "_")
    return re.sub(r'[^a-z0-9_]', '', name)


# ------------------- FOLDER LOGIC -------------------
def categorize_and_move(file_path: str, doc_type: str, base_folder: Path, loan_type: str):
    """Classify and move file into appropriate subfolder."""
    doc_type_lower = doc_type.lower()

    # Detect category
    if any(x in doc_type_lower for cat in KYC_DOCS.values() for x in cat):
        target_folder = "KYC Docs"
    elif any(x in doc_type_lower for x in INCOME_DOCS):
        target_folder = "Income Docs"
    elif any(x in doc_type_lower for x in PROPERTY_DOCS):
        target_folder = "Property Docs"
    elif any(x in doc_type_lower for x in BUSINESS_PROOF):
        target_folder = "Business Proof"
    else:
        target_folder = "Others"

    # Create full path: base_folder/loan_type/category/
    folder_path = base_folder / loan_type / target_folder
    folder_path.mkdir(parents=True, exist_ok=True)

    # Sanitize filename and handle duplicates
    clean_name = sanitize_filename(doc_type)
    ext = os.path.splitext(file_path)[1]
    counter = 1
    new_filename = f"{clean_name}{ext}"
    while (folder_path / new_filename).exists():
        counter += 1
        new_filename = f"{clean_name}_{counter}{ext}"

    dest_path = folder_path / new_filename
    shutil.move(file_path, dest_path)

    print(f"📁 {os.path.basename(file_path)} → {loan_type}/{target_folder}/{new_filename} ({doc_type})")


# ------------------- MAIN LOGIC -------------------
def organize_documents_for_loan(loan_type: str, input_folder: Path = None):
    """
    Recognize and organize all documents dynamically.
    Works anywhere inside the project.
    """

    # Detect project root (where .env or main.py lives)
    project_root = Path(__file__).resolve().parent.parent

    # Input folder (defaults to /new_all_samples)
    if input_folder is None:
        input_folder = project_root / "new_all_samples"

    # Output base folder (/organized_docs)
    base_folder = project_root / "organized_docs"
    base_folder.mkdir(parents=True, exist_ok=True)

    # Collect all image/pdf files
    files_to_check = [
        str(file)
        for file in input_folder.glob("*")
        if file.suffix.lower() in [".jpg", ".jpeg", ".png", ".pdf"]
    ]

    if not files_to_check:
        print(f"⚠️ No input files found in: {input_folder}")
        return

    print(f"\n🔍 Recognizing and organizing documents for: {loan_type}")
    print(f"📂 Input folder: {input_folder}")
    print(f"📂 Output folder: {base_folder}\n")

    for file in files_to_check:
        result = recognize_document(file)
        print(f"📄 {os.path.basename(file)} → {result}")
        doc_type = (
            result.split(":")[-1]
            .replace("}", "")
            .replace('"', "")
            .strip()
        )
        categorize_and_move(file, doc_type, base_folder, loan_type)

    print("\n✅ All documents organized successfully!")


# ------------------- RUN EXAMPLE -------------------
if __name__ == "__main__":
    organize_documents_for_loan("Home Loan")
