
import os
import shutil
from pathlib import Path


# ─── CONFIGURATION ────────────────────────────────────────────────────────────
JOBS = [
    {
        "label": "8K Files",
        "source": "/Users/necsi/Documents/ukrainian-collections-app/public/hermitage_images",          # ← change this
        "dest_base": "/Users/necsi/Documents/hermitage",     # ← change this
        "num_folders": 4,                        # folders 1,2,3,4
        "pattern": "*",                          # all file types
    }
 #   ,
  #  {
#        "label": "30K Images",
#        "source": "/path/to/30k/images",         # ← change this
#        "dest_base": "/path/to/destination",     # ← same or different base
#        "num_folders": 6,                        # 6 folders → ~5,000 each
#        "pattern": "*.jpg,*.jpeg,*.png,*.webp,*.gif,*.tiff",  # image types only
#    },
]
# ──────────────────────────────────────────────────────────────────────────────


def move_batch(label: str, source_dir: str, dest_base_dir: str,
               num_folders: int, pattern: str) -> None:
    source = Path(source_dir)
    dest_base = Path(dest_base_dir)

    if not source.exists() or not source.is_dir():
        print(f"[{label}] ✗ Source not found: {source}\n")
        return

    # Collect files matching one or more glob patterns
    patterns = [p.strip() for p in pattern.split(",")]
    files = []
    for p in patterns:
        files.extend([f for f in source.glob(p) if f.is_file()])
    files = sorted(set(files))  # deduplicate & sort

    total = len(files)
    if total == 0:
        print(f"[{label}] No matching files found.\n")
        return

    # Create numbered destination folders
    folders = []
    for i in range(1, num_folders + 1):
        folder = dest_base / str(i)
        folder.mkdir(parents=True, exist_ok=True)
        folders.append(folder)

    batch_size = -(-total // num_folders)  # ceiling division

    print(f"\n{'═' * 50}")
    print(f"  JOB      : {label}")
    print(f"  Source   : {source}")
    print(f"  Dest     : {dest_base} → folders 1–{num_folders}")
    print(f"  Files    : {total:,}  (~{batch_size:,} per folder)")
    print(f"{'═' * 50}")

    moved_total, failed_total = 0, []
    folder_counts = [0] * num_folders

    for idx, file in enumerate(files):
        bucket = min(idx // batch_size, num_folders - 1)
        target = folders[bucket] / file.name

        # Resolve naming conflict
        if target.exists():
            target = folders[bucket] / f"{file.stem}_{idx}{file.suffix}"

        try:
            shutil.move(str(file), str(target))
            folder_counts[bucket] += 1
            moved_total += 1
        except Exception as e:
            failed_total.append((file.name, str(e)))

        # Progress every 1,000 files
        if (idx + 1) % 1000 == 0 or (idx + 1) == total:
            pct = (idx + 1) / total * 100
            print(f"  [{pct:5.1f}%]  {idx + 1:,} / {total:,} processed", end="\r")

    print()  # newline after progress line

    # Per-folder summary
    print(f"\n  {'Folder':<10} {'Files Moved':>12}")
    print(f"  {'─'*24}")
    for i, count in enumerate(folder_counts):
        print(f"  Folder {i+1:<5} {count:>12,}")
    print(f"  {'─'*24}")
    print(f"  {'TOTAL':<10} {moved_total:>12,}")
    if failed_total:
        print(f"\n  ✗ Failed ({len(failed_total)}):")
        for name, err in failed_total[:10]:  # show first 10 failures
            print(f"    {name}: {err}")
        if len(failed_total) > 10:
            print(f"    ... and {len(failed_total) - 10} more")


if __name__ == "__main__":
    for job in JOBS:
        move_batch(
            label=job["label"],
            source_dir=job["source"],
            dest_base_dir=job["dest_base"],
            num_folders=job["num_folders"],
            pattern=job["pattern"],
        )
    print(f"\n{'═' * 50}")
    print("  All jobs complete.")
    print(f"{'═' * 50}\n")
