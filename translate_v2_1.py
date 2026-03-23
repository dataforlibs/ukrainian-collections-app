"""
translate_v2.py — Fixed version.
- Batch size reduced to 20 rows (was 50)
- max_tokens increased to 4096 (was 1024)
- Translates only ONE field per API call to keep responses small
- Saves checkpoint as it goes

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python translate_v2.py
"""

import os, json, time
import anthropic
import pandas as pd

INPUT_CSV       = "combined_database.csv"
OUTPUT_CSV      = "combined_database_translated.csv"
CHECKPOINT_FILE = "translations_v2_checkpoint.jsonl"
BATCH_SIZE      = 20    # reduced from 50
MODEL           = "claude-haiku-4-5-20251001"

FIELDS = {
    "Название":       "Назва_uk",
    "Место создания": "Місце_створення_uk",
    "Место находки":  "Місце_знахідки_uk",
}

SYSTEM_PROMPT = """You are a translator from Russian to Ukrainian for museum artifact metadata.
Translate the values in the given JSON. Keys are row indices (strings), values are Russian text.
Return ONLY a JSON object with the same keys and Ukrainian translations as values.
If a value is empty or null return it unchanged. No explanation, no markdown, just JSON."""

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

print(f"Loading {INPUT_CSV}...")
df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")
print(f"Loaded {len(df):,} rows.")

# Cost estimate
n_batches = (len(df) // BATCH_SIZE + 1) * len(FIELDS)
est_input  = n_batches * 800
est_output = n_batches * 600
est_cost   = ((est_input / 1e6) * 0.80 + (est_output / 1e6) * 4.00) * 0.50
print(f"\nEstimated cost (Batch API): ~${est_cost:.2f}")
print(f"Total batch requests: {n_batches:,}")

# Build requests — one field at a time
requests = []
for field_ru, field_uk in FIELDS.items():
    for i in range(0, len(df), BATCH_SIZE):
        chunk = df.iloc[i:i + BATCH_SIZE]
        payload = {str(idx): str(row.get(field_ru, "") or "")
                   for idx, row in chunk.iterrows()}
        requests.append({
            "custom_id": f"f{list(FIELDS.values()).index(field_uk)}__{i}",
            "params": {
                "model": MODEL,
                "max_tokens": 4096,
                "system": SYSTEM_PROMPT,
                "messages": [{
                    "role": "user",
                    "content": f"Translate Russian to Ukrainian:\n{json.dumps(payload, ensure_ascii=False)}"
                }]
            }
        })

print(f"\nSubmitting {len(requests):,} requests to Batch API...")
batch = client.messages.batches.create(requests=requests)
batch_id = batch.id
print(f"Batch ID: {batch_id}")
with open("batch_id_v2.txt", "w") as f:
    f.write(batch_id)
print("Saved to batch_id_v2.txt")

# Poll
print("\nPolling... (Ctrl+C to stop, run retrieve_v2.py later)")
while True:
    status = client.messages.batches.retrieve(batch_id)
    c = status.request_counts
    print(f"  {status.processing_status} | OK:{c.succeeded} | Running:{c.processing} | Err:{c.errored}")
    if status.processing_status == "ended":
        break
    time.sleep(60)

# Retrieve
print(f"\nRetrieving results -> {CHECKPOINT_FILE}")
saved = errors = 0
with open(CHECKPOINT_FILE, "w", encoding="utf-8") as ckpt:
    for result in client.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            errors += 1
            continue
        raw = result.result.message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        try:
            translations = json.loads(raw)
            ckpt.write(json.dumps({
                "custom_id": result.custom_id,
                "translations": translations
            }, ensure_ascii=False) + "\n")
            saved += 1
            if saved % 200 == 0:
                print(f"  Saved {saved} batches...")
        except json.JSONDecodeError as e:
            errors += 1
            print(f"  Parse error {result.custom_id}: {e}")

print(f"\nCheckpoint: {saved} OK, {errors} errors")

# Apply
print(f"\nApplying to CSV...")
for col in FIELDS.values():
    df[col] = ""

with open(CHECKPOINT_FILE, encoding="utf-8") as ckpt:
    for line in ckpt:
        rec = json.loads(line)
        # custom_id format: "f0__1000", "f1__1000", "f2__1000"
        parts = rec["custom_id"].split("__")
        field_idx = int(parts[0][1:])  # strip leading 'f'
        field_uk = list(FIELDS.values())[field_idx]
        for str_idx, value in rec["translations"].items():
            idx = int(str_idx)
            if idx < len(df):
                df.at[idx, field_uk] = value

df.to_csv(OUTPUT_CSV, index=False)
filled = (df["Назва_uk"] != "").sum()
print(f"Done! Saved {OUTPUT_CSV}")
print(f"Rows translated: {filled:,} / {len(df):,}")
