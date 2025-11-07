import os
import subprocess
import time
from pathlib import Path

steps = [
    "automation/1_recognize_and_place_docs.py",
    "automation/2_recognize_and_get_json.py",
    "automation/3_correct_the_json.py",
    "automation/4_generate_json_schema.py",
    "automation/5_auto_form_filler_with_schema.py",
]

overall_start = time.time()

for step in steps:
    print(f"\n🚀 Running: {step}")
    start_time = time.time()
    
    result = subprocess.run(["python", step])
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"✅ Completed {step} in {duration:.2f} seconds")

overall_end = time.time()
total_duration = overall_end - overall_start

print(f"\n⏱️ All automation steps finished in {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
