import pytesseract
from PIL import Image

# ✅ If you're on Windows, specify the path manually (optional)
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load your image file
image_path = "./12 month bank.png"  # Replace with your image filename
img = Image.open(image_path)

# Extract text using pytesseract
extracted_text = pytesseract.image_to_string(img)

# Print the extracted text
print("📝 Extracted Text:")
print(extracted_text)
