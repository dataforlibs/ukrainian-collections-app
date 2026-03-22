"""
Convert old Hermitage image URLs to new hermitagemuseum.org format.

Old format:
  https://collections.hermitage.ru/api/spf/{HASH}.jpg?w=1000&h=1000

New format:
  https://hermitagemuseum.org/api/files/fshow?needlePath=%2Fapi%2Fspf%2F{HASH}.jpg%3Fw%3D1600%26h%3D1600
"""

import csv
import urllib.parse
import re
import sys
from pathlib import Path


def convert_hermitage_url(old_url):
    """Convert a collections.hermitage.ru URL to hermitagemuseum.org format."""
    if not old_url or 'collections.hermitage.ru' not in old_url:
        return old_url

    # Extract the /api/spf/... path with query params
    match = re.search(r'(/api/spf/.+)$', old_url)
    if not match:
        return old_url

    path = match.group(1)

    # Replace dimensions: use 1600x1600 for the new format
    path = re.sub(r'w=\d+', 'w=1600', path)
    path = re.sub(r'h=\d+', 'h=1600', path)

    # URL-encode the path
    encoded_path = urllib.parse.quote(path, safe='')

    return f'https://hermitagemuseum.org/api/files/fshow?needlePath={encoded_path}'


def main():
    input_file = Path('combined_database.csv')
    output_file = Path('combined_database_updated.csv')

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        sys.exit(1)

    converted = 0
    skipped = 0
    total = 0

    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8', newline='') as outfile:

        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
        writer.writeheader()

        for row in reader:
            total += 1
            museum = row.get('museum', '').strip().lower()
            img = row.get('img', '').strip()

            # Only convert non-SHM (i.e., Hermitage) rows
            if museum != 'shm' and 'collections.hermitage.ru' in img:
                row['img'] = convert_hermitage_url(img)
                converted += 1
            else:
                skipped += 1

            writer.writerow(row)

    print(f"Done!")
    print(f"  Total rows:   {total}")
    print(f"  Converted:    {converted}")
    print(f"  Skipped:      {skipped}")
    print(f"  Output saved: {output_file}")


if __name__ == '__main__':
    main()
