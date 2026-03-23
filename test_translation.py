"""
Quick quality test — translates 5 rows instantly using regular API.
Run this BEFORE waiting for the batch to finish.

Usage:
    python test_translation.py
"""
import os, json
import anthropic
import pandas as pd

df = pd.read_csv("combined_database.csv", dtype=str).fillna("")

# Take 5 diverse samples
samples = df[["Название", "Место создания", "Место находки"]].dropna(how="all").head(5)

SYSTEM_PROMPT = """You are a translator from Russian to Ukrainian for museum artifact metadata.
Translate the values in the given JSON. Keys are row indices (strings), values are Russian text.
Return ONLY a JSON object with the same keys and Ukrainian translations as values.
If a value is empty or null return it unchanged. No explanation, no markdown, just JSON."""

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

for field in ["Название", "Место создания", "Место находки"]:
    payload = {str(i): str(v) for i, v in samples[field].items() if v}
    if not payload:
        continue

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user",
                   "content": f"Translate Russian to Ukrainian:\n{json.dumps(payload, ensure_ascii=False)}"}]
    )
    result = json.loads(resp.content[0].text.strip())

    print(f"\n{'='*60}")
    print(f"FIELD: {field}")
    print(f"{'='*60}")
    for idx, uk_val in result.items():
        ru_val = payload.get(idx, "")
        print(f"  RU: {ru_val}")
        print(f"  UK: {uk_val}")
        print()
