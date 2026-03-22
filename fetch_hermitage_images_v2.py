"""
Download Hermitage images from combined_database_updated.csv

Uses curl instead of Python requests — the Hermitage site uses QRATOR
DDoS protection which curl handles correctly out of the box.

Usage:
    python fetch_hermitage_images_v2.py

Images saved to ./hermitage_images/ named by row ID.
Skips already-downloaded files so you can stop and resume anytime.
"""

import csv
import time
import subprocess
import sys
from pathlib import Path


# --- Configuration ---
INPUT_FILE = 'combined_database_updated.csv'
OUTPUT_DIR = 'hermitage_images'
DELAY = 1.0  # seconds between requests (be respectful)
TIMEOUT = 30
MAX_RETRIES = 3


def download_image(url, filepath, retries=MAX_RETRIES):
    """Download using curl (handles QRATOR/SSL correctly)."""
    for attempt in range(retries):
        try:
            result = subprocess.run(
                [
                    'curl', '-s', '-o', str(filepath),
                    '-w', '%{http_code}',
                    '--max-time', str(TIMEOUT),
                    '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    '-H', 'Accept: image/webp,image/apng,image/*,*/*;q=0.8',
                    '-H', 'Referer: https://hermitagemuseum.org/',
                    url
                ],
                capture_output=True, text=True, timeout=TIMEOUT + 10
            )
            status = result.stdout.strip()

            if status == '200' and filepath.exists() and filepath.stat().st_size > 1000:
                return True
            elif status == '429':
                wait = (attempt + 1) * 5
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"    HTTP {status}")
                return False
        except subprocess.TimeoutExpired:
            print(f"    Timeout (attempt {attempt + 1}/{retries})")
        except Exception as e:
            print(f"    Error: {e}")
            return False
    return False


def main():
    input_path = Path(INPUT_FILE)
    output_dir = Path(OUTPUT_DIR)

    if not input_path.exists():
        print(f"Error: {input_path} not found")
        print(f"Run convert_hermitage_urls.py first.")
        sys.exit(1)

    output_dir.mkdir(exist_ok=True)

    # Collect Hermitage rows
    rows = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            museum = row.get('museum', '').strip().lower()
            img = row.get('img', '').strip()
            if museum != 'shm' and 'hermitagemuseum.org' in img:
                rows.append(row)

    print(f"Found {len(rows)} Hermitage images to download")
    print(f"Saving to: {output_dir}/")
    print()

    downloaded = 0
    skipped = 0
    failed = 0
    failed_ids = []

    for i, row in enumerate(rows):
        row_id = row.get('id', row.get('ID', str(i)))
        img_url = row.get('img', '').strip()

        filename = f"{row_id}.jpg"
        filepath = output_dir / filename

        # Skip if already downloaded
        if filepath.exists() and filepath.stat().st_size > 1000:
            skipped += 1
            continue

        print(f"[{i + 1}/{len(rows)}] ID: {row_id} ... ", end='', flush=True)

        if download_image(img_url, filepath):
            size_kb = filepath.stat().st_size / 1024
            print(f"OK ({size_kb:.0f} KB)")
            downloaded += 1
        else:
            print("FAILED")
            failed += 1
            failed_ids.append(row_id)
            if filepath.exists():
                filepath.unlink()

        time.sleep(DELAY)

    # Summary
    print()
    print("=" * 40)
    print(f"Downloaded:  {downloaded}")
    print(f"Skipped:     {skipped} (already existed)")
    print(f"Failed:      {failed}")
    print(f"Total:       {len(rows)}")

    if failed_ids:
        failed_log = output_dir / 'failed.txt'
        with open(failed_log, 'w') as f:
            f.write('\n'.join(str(fid) for fid in failed_ids))
        print(f"\nFailed IDs saved to: {failed_log}")


if __name__ == '__main__':
    main()
