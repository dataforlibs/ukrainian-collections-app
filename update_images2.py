
import os
import pandas as pd

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
BASE_DIR    = "/Users/necsi/Documents"
SCRIPT_DIR  = "/Users/necsi/Documents/ukrainian-collections-app/public"
CSV_FILE    = os.path.join(SCRIPT_DIR, "combined_database_updated.csv")

DIRECTORIES = [
    os.path.join(BASE_DIR, "herm_1"),
    os.path.join(BASE_DIR, "herm_2"),
    os.path.join(BASE_DIR, "herm_3"),
    os.path.join(BASE_DIR, "herm_4"),
]

# Folder names as they will appear in the recorded path (relative, for web use)
DIR_LABELS = {
    os.path.join(BASE_DIR, "herm_1"): "herm_1",
    os.path.join(BASE_DIR, "herm_2"): "herm_2",
    os.path.join(BASE_DIR, "herm_3"): "herm_3",
    os.path.join(BASE_DIR, "herm_4"): "herm_4",
}

IMG_COL = "img1"
ID_COL  = "id"
# ──────────────────────────────────────────────────────────────────────────────


def build_image_index(directories, dir_labels):
    """
    Scan all directories and return a dict: { file_stem → '/herm_X/stem.jpg' }
    Uses dir_labels to build clean relative paths regardless of absolute location.
    """
    index = {}
    for folder in directories:
        if not os.path.isdir(folder):
            print(f"  [WARN] Directory not found, skipping: {folder}")
            continue

        label    = dir_labels[folder]
        files    = os.listdir(folder)
        img_files = [f for f in files
                     if os.path.splitext(f)[1].lower()
                     in (".jpg", ".jpeg", ".png", ".tif", ".tiff")]

        print(f"  {label:10s} → {folder}")
        print(f"             {len(img_files):,} image files found")

        for fname in img_files:
            stem = os.path.splitext(fname)[0]
            path = f"/{label}/{stem}.jpg"

            if stem in index:
                print(f"  [WARN] Duplicate id '{stem}' in {label} "
                      f"(already mapped to {index[stem]})")
            else:
                index[stem] = path

    return index


def fill_img1(csv_file, image_index, id_col, img_col):
    """
    Load CSV, fill empty img1 cells where id matches a file in image_index.
    """
    df = pd.read_csv(csv_file, dtype=str)
    df.columns = df.columns.str.strip()

    if id_col not in df.columns:
        raise ValueError(
            f"Column '{id_col}' not found in CSV.\n"
            f"Available columns: {list(df.columns)}"
        )

    # Create img1 column if it doesn't exist
    if img_col not in df.columns:
        df[img_col] = ""
        print(f"  [INFO] Column '{img_col}' did not exist — created.")

    total_rows   = len(df)
    already_filled = df[img_col].notna() & (df[img_col].str.strip() != "")
    empty_mask   = ~already_filled

    print(f"\n  Total rows        : {total_rows:,}")
    print(f"  Already filled    : {already_filled.sum():,}")
    print(f"  Empty (to fill)   : {empty_mask.sum():,}")

    matched   = 0
    unmatched = []

    for idx in df[empty_mask].index:
        row_id = str(df.at[idx, id_col]).strip()

        if row_id in image_index:
            df.at[idx, img_col] = image_index[row_id]
            matched += 1
        else:
            unmatched.append(row_id)

    # Save back to CSV
    df.to_csv(csv_file, index=False)

    return matched, unmatched


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("=" * 55)
    print("  Image → CSV matcher")
    print("=" * 55)
    print(f"\n  CSV file  : {CSV_FILE}")
    print(f"  Image base: {BASE_DIR}\n")

    print("Step 1 — Scanning image directories...")
    print("-" * 55)
    image_index = build_image_index(DIRECTORIES, DIR_LABELS)
    print("-" * 55)
    print(f"  Total unique images indexed: {len(image_index):,}\n")

    print("Step 2 — Matching ids and filling img1...")
    print("-" * 55)
    matched, unmatched = fill_img1(CSV_FILE, image_index, ID_COL, IMG_COL)

    print(f"\n{'=' * 55}")
    print(f"  Matched & filled  : {matched:,} rows")
    print(f"  No image found    : {len(unmatched):,} rows")
    print(f"{'=' * 55}")

    if unmatched:
        print(f"\n  IDs with no matching image file (first 20):")
        for uid in unmatched[:20]:
            print(f"    - {uid}")
        if len(unmatched) > 20:
            print(f"    ... and {len(unmatched) - 20} more")

        # Optional: save unmatched ids to a log file for review
        log_path = os.path.join(SCRIPT_DIR, "unmatched_ids.txt")
        with open(log_path, "w") as f:
            f.write("\n".join(unmatched))
        print(f"\n  Full unmatched list saved → {log_path}")

    print(f"\n  CSV saved → {CSV_FILE}\n")
