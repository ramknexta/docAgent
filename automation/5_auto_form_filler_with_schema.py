import os, json, re, time
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from pathlib import Path

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Gemini imports
import google.generativeai as genai

# ---------------------------------------------------------
# STEP 1: Load environment and configure Gemini
# ---------------------------------------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY") or "YOUR_GEMINI_API_KEY")

# ---------------------------------------------------------
# STEP 2: Utility - Flatten JSON
# ---------------------------------------------------------
def flatten_json(data: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_json(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.extend(flatten_json(item, f"{new_key}[{i}]", sep=sep).items())
                else:
                    items.append((f"{new_key}[{i}]", item))
        else:
            items.append((new_key, v))
    return dict(items)


# ---------------------------------------------------------
# STEP 3: Load multiple user data JSON files
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]

json_corrected_folder = BASE_DIR / "json_corrected"
schema_folder = BASE_DIR / "schema"
forms_folder = BASE_DIR / "forms"

user_data = {}
for file in json_corrected_folder.glob("*.json"):
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
        flattened = flatten_json(data)
        user_data.update(flattened)

# ---------------------------------------------------------
# STEP 4: Load Form Schema
# ---------------------------------------------------------
schema_file = schema_folder / "form_schema.json"
with open(schema_file, "r", encoding="utf-8") as f:
    form_schema = json.load(f)

flattened_schema = flatten_json(form_schema)

# ---------------------------------------------------------
# STEP 5: Use Gemini to map HTML form fields via schema
# ---------------------------------------------------------
form_path = forms_folder / "form.html"
html_fields = re.findall(r'name="([^"]+)"', open(form_path, "r", encoding="utf-8").read())

prompt = f"""
You are an expert in intelligent data mapping.

We have:
1. HTML form fields (to be filled via Selenium)
2. Form schema (defines what each field represents)
3. User data keys (from KYC, Income, Property docs)

### HTML Input Names:
{html_fields}

### Form Schema Keys:
{list(flattened_schema.keys())}

### User Data Keys:
{list(user_data.keys())}

Task:
Map each HTML input/select field name to the most relevant user data key.
Return pure JSON, no markdown or explanation.
"""

model = genai.GenerativeModel("gemini-2.0-flash")
response = model.generate_content(prompt)
mapping_response = response.text.strip()

try:
    json_text = re.search(r"\{.*\}", mapping_response, re.S).group()
    field_mapping = json.loads(json_text)
except Exception:
    print("⚠️ Gemini mapping parse error. Using empty mapping.")
    field_mapping = {}

# ---------------------------------------------------------
# STEP 6: Launch Selenium
# ---------------------------------------------------------
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.maximize_window()
driver.get("file://" + str(form_path.resolve()))
wait = WebDriverWait(driver, 10)
time.sleep(2)

# ---------------------------------------------------------
# STEP 7: Autofill Functionality
# ---------------------------------------------------------
filled_response = {}

def reveal_hidden_fields(driver):
    driver.execute_script("""
        document.querySelectorAll('.hidden').forEach(el => el.classList.remove('hidden'));
        document.querySelectorAll('[style*="display:none"]').forEach(el => el.style.display = 'block');
    """)

def safe_fill(element, value):
    """Robustly fills input or textarea with visibility handling."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.2)
    try:
        # Try normal way first
        element.clear()
        element.send_keys(str(value))
    except Exception:
        try:
            # Try forcing visibility and typing again
            driver.execute_script("""
                arguments[0].style.display = 'block';
                arguments[0].style.visibility = 'visible';
            """, element)
            time.sleep(0.2)
            element.clear()
            element.send_keys(str(value))
        except Exception:
            # Last fallback: directly set value via JavaScript
            driver.execute_script("arguments[0].value = arguments[1];", element, str(value))


def fill_fields(page_name):
    print(f"\n📄 Filling {page_name}...")
    reveal_hidden_fields(driver)

    for html_name, json_key in field_mapping.items():
        value = user_data.get(json_key, "")
        if not value:
            continue

        try:
            element = wait.until(EC.presence_of_element_located((By.NAME, html_name)))
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            tag = element.tag_name.lower()

            if tag == "select":
                select = Select(element)
                try:
                    select.select_by_visible_text(str(value))
                except Exception:
                    # fallback: match ignoring case
                    for option in select.options:
                        if option.text.strip().lower() == str(value).strip().lower():
                            option.click()
                            break
                filled_response[html_name] = value
            else:
                safe_fill(element, value)
                filled_response[html_name] = value

            print(f"✅ Filled '{html_name}' → {value}")

        except TimeoutException:
            pass

# ---------------------------------------------------------
# STEP 8: Fill Pages
# ---------------------------------------------------------
fill_fields("Page 1")

try:
    next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]")))
    next_btn.click()
    time.sleep(1)
except Exception:
    pass

fill_fields("Page 2")

# ---------------------------------------------------------
# STEP 9: Submit Form
# ---------------------------------------------------------
try:
    reveal_hidden_fields(driver)
    submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit']")))
    submit_btn.click()
    print("\n📤 Form submitted successfully!")
except Exception as e:
    print("⚠️ Could not submit form:", e)

time.sleep(2)
driver.quit()

# ---------------------------------------------------------
# STEP 10: Summary
# ---------------------------------------------------------
print("\n✅ FINAL FILLED INPUTS:")
for field, value in filled_response.items():
    print(f"• {field} → {value}")
