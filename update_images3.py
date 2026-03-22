
"""
Fetch Hermitage images for IDs listed in unmatched_ids.txt,
save to herm_1/, and update img1 in combined_database_updated.csv.

Based on fetch_hermitage_images_v2.py — uses curl to bypass QRATOR protection.

Usage:
    python fetch_hermitage_unmatched.py
"""

import csv
import time
import subprocess
import sys
from pathlib import Path

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
BASE_DIR        = Path("/Users/necsi/Documents")
SCRIPT_DIR      = Path("/Users/necsi/Documents/ukrainian-collections-app/public")

CSV_FILE        = SCRIPT_DIR / "combined_database_updated.csv"
UNMATCHED_FILE  = SCRIPT_DIR / "unmatched_ids.txt"
OUTPUT_DIR      = BASE_DIR / "herm_1"

ID_COL          = "id"
IMG_SRC_COL     = "img"        # column that already has the hermitage URL
IMG_DEST_COL    = "img1"       # column to fill in

DELAY           = 2.0          # seconds between requests
TIMEOUT         = 30
MAX_RETRIES     = 3
# ──────────────────────────────────────────────────────────────────────────────


def load_unmatched_ids(path):
    with open(path, "r", encoding="utf-8") as f:
        ids = {line.strip() for line in f if line.strip()}
    print(f"  Loaded {len(ids):,} unmatched IDs from {path.name}")
    return ids


def build_url_index(csv_path, id_col, img_src_col, target_ids):
    """
    Read the CSV and return a dict { id → hermitage_image_url }
    only for rows whose id is in target_ids AND img_src_col contains
    a hermitage URL.
    """
    index = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Normalise column names
        reader.fieldnames = [c.strip() for c in reader.fieldnames]
        for row in reader:
            row_id  = row.get(id_col,      "").strip()
            img_url = row.get(img_src_col, "").strip()
            if row_id in target_ids and "hermitagemuseum.org" in img_url:
                index[row_id] = img_url

    print(f"  Matched {len(index):,} IDs to Hermitage URLs in CSV")
    return index


def download_image(url, filepath, retries=MAX_RETRIES):
    """Download using curl — handles QRATOR/SSL correctly."""
    for attempt in range(retries):
        try:
            result = subprocess.run(
                [
                    "curl", "-L", "-s",
                    "-o", str(filepath),
                    "-w", "%{http_code}",
                    "--max-time", str(TIMEOUT),
                    "-H", ("User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36"),
                    "-H", "Accept: image/webp,image/apng,image/*,*/*;q=0.8",
                    "-H", "Accept-Language: en-US,en;q=0.9",
                    "-H", "Referer: https://hermitagemuseum.org/",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT + 10,
            )
            status = result.stdout.strip()

            if status == "200" and filepath.exists() and filepath.stat().st_size > 1000:
                return True
            elif status == "429":
                wait = (attempt + 1) * 10
                print(f"      Rate limited — waiting {wait}s...")
                time.sleep(wait)
            elif status == "404":
                print(f"      HTTP 404 — not found on server")
                return False
            else:
                print(f"      HTTP {status} (attempt {attempt + 1}/{retries})")
                time.sleep(3)

        except subprocess.TimeoutExpired:
            print(f"      Timeout (attempt {attempt + 1}/{retries})")
            time.sleep(3)
        except Exception as e:
            print(f"      Error: {e}")
            return False

    return False


def update_csv(csv_path, id_col, img_dest_col, updates):
    """
    Rewrite the CSV applying all {id → new_img1_value} updates at once.
    Much faster than re-reading the file per row.
    """
    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = [c.strip() for c in reader.fieldnames]
        if img_dest_col not in fieldnames:
            fieldnames.append(img_dest_col)
        for row in reader:
            row_id = row.get(id_col, "").strip()
            if row_id in updates:
                row[img_dest_col] = updates[row_id]
            rows.append(row)

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  CSV updated — {len(updates):,} img1 entries written")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 58)
    print("  Hermitage unmatched image fetcher")
    print("=" * 58)

    # Validate paths
    for p in [CSV_FILE, UNMATCHED_FILE]:
        if not p.exists():
            print(f"[ERROR] File not found: {p}")
            sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load IDs and match to URLs ──
    target_ids = load_unmatched_ids(UNMATCHED_FILE)
    url_index  = build_url_index(CSV_FILE, ID_COL, IMG_SRC_COL, target_ids)

    no_url = [i for i in target_ids if i not in url_index]
    if no_url:
        print(f"  [WARN] {len(no_url):,} IDs have no Hermitage URL in CSV "
              f"— they will be skipped")

    if not url_index:
        print("\n  Nothing to download. Exiting.")
        sys.exit(0)

    print(f"\n  Output dir : {OUTPUT_DIR}")
    print(f"  To fetch   : {len(url_index):,} images\n")

    # ── Download loop ──
    csv_updates = {}          # { id → '/herm_1/id.jpg' } — applied at the end
    downloaded, skipped, failed = 0, 0, 0
    failed_ids = []

    items = sorted(url_index.items())   # stable order for resume runs

    for i, (row_id, img_url) in enumerate(items, 1):
        filepath = OUTPUT_DIR / f"{row_id}.jpg"

        # Resume: skip already-downloaded files
        if filepath.exists() and filepath.stat().st_size > 1000:
            csv_updates[row_id] = f"/herm_1/{row_id}.jpg"
            skipped += 1
            continue

        print(f"[{i:>4}/{len(items)}]  {row_id}")
        print(f"          {img_url}")

        ok = download_image(img_url, filepath)

        if ok:
            size_kb = filepath.stat().st_size / 1024
            print(f"          → saved  ({size_kb:.0f} KB)")
            csv_updates[row_id] = f"/herm_1/{row_id}.jpg"
            downloaded += 1
        else:
            print(f"          → FAILED")
            failed_ids.append(row_id)
            failed += 1
            if filepath.exists():
                filepath.unlink()          # remove partial file

        time.sleep(DELAY)

    # ── Bulk-update the CSV once at the end ──
    if csv_updates:
        print(f"\nUpdating CSV...")
        update_csv(CSV_FILE, ID_COL, IMG_DEST_COL, csv_updates)

    # ── Summary ──
    print(f"\n{'=' * 58}")
    print(f"  Downloaded   : {downloaded:>5}")
    print(f"  Skipped      : {skipped:>5}  (already existed)")
    print(f"  Failed       : {failed:>5}")
    print(f"  No URL found : {len(no_url):>5}  (not in CSV)")
    print(f"{'=' * 58}")

    # Save failed IDs for next pass
    if failed_ids:
        fail_log = SCRIPT_DIR / "still_missing.txt"
        with open(fail_log, "w") as f:
            f.write("\n".join(str(fid) for fid in failed_ids))
        print(f"\n  Failed IDs   → {fail_log}")

    print(f"  CSV saved    → {CSV_FILE}")
    print(f"  Images saved → {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
