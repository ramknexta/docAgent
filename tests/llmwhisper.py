import os
import json
import time
from dotenv import load_dotenv
from unstract.llmwhisperer import LLMWhispererClientV2
from unstract.llmwhisperer.client_v2 import LLMWhispererClientException

# Load environment variables
load_dotenv()

def get_client():
    """Initialize LLMWhisperer client using API key from .env"""
    base_url = os.getenv("LLMWHISPERER_BASE_URL_V2", "https://llmwhisperer-api.us-central.unstract.com/api/v2")
    api_key = os.getenv("LLMWHISPERER_API_KEY")

    if not api_key:
        raise ValueError("❌ API key not found. Please set LLMWHISPERER_API_KEY in your .env file")

    return LLMWhispererClientV2(base_url=base_url, api_key=api_key)

def extract_document_text(file_path, timeout=300):
    """Extract plain text from document"""
    client = get_client()
    try:
        result = client.whisper(
            file_path=file_path,
            wait_for_completion=True,
            wait_timeout=timeout
        )

        # Extract only text content
        text = result.get("extraction", {}).get("result_text", "")

        if not text:
            print("⚠️ No text found in the document.")
        return text.strip()

    except LLMWhispererClientException as e:
        print(f"❌ Error: {e.message} (Status Code: {e.status_code})")
        return None


if __name__ == "__main__":
    file_path = "./12 month bank.png"

    print("🚀 Extracting text from document...")
    extracted_text = extract_document_text(file_path)

    if extracted_text:
        print("\n✅ Extraction complete! Here's the extracted text:\n")
        print("---------------------------------------------------")
        print(extracted_text)
        print("---------------------------------------------------")
    else:
        print("❌ Failed to extract text.")
