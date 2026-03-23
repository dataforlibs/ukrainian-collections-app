"""
Run this AFTER the batch has completed if you stopped translate_csv.py early.
Reads the batch_id from batch_id.txt and applies results to the CSV.

Usage:
    python retrieve_results.py
"""

import os, json
import anthropic
import pandas as pd

INPUT_CSV  = "combined_database.csv"
OUTPUT_CSV = "combined_database_translated.csv"

FIELDS = {
    "Название":       "Назва_uk",
    "Место создания": "Місце_створення_uk",
    "Место находки":  "Місце_знахідки_uk",
}

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

with open("batch_id.txt") as f:
    batch_id = f.read().strip()

print(f"Retrieving batch: {batch_id}")
status = client.messages.batches.retrieve(batch_id)
print(f"Status: {status.processing_status}")
print(f"Succeeded: {status.request_counts.succeeded} | "
      f"Errors: {status.request_counts.errored}")

if status.processing_status != "ended":
    print("Batch not finished yet. Try again later.")
    exit()

df = pd.read_csv(INPUT_CSV, dtype=str)
for col_uk in FIELDS.values():
    df[col_uk] = ""

results = {}
for result in client.messages.batches.results(batch_id):
    if result.result.type != "succeeded":
        continue
    raw = result.result.message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        results[result.custom_id] = json.loads(raw)
    except Exception as e:
        print(f"  Parse error {result.custom_id}: {e}")

for custom_id, translations in results.items():
    start_idx = int(custom_id.split("_")[1])
    for str_idx, row_t in translations.items():
        idx = int(str_idx)
        for ru_col, uk_col in FIELDS.items():
            df.at[idx, uk_col] = row_t.get(ru_col, "")

df.to_csv(OUTPUT_CSV, index=False)
print(f"\nSaved {OUTPUT_CSV} with {len(results)*50:,} rows translated.")
