"""
detection/download_ppe_dataset.py
Step 8 — Download a labeled PPE dataset (helmet + vest) from Roboflow Universe.

Uses the public export URL (no API key needed for public datasets).
Downloads YOLOv8-format labels: images/ + labels/ folders.

Dataset: PPE Detection (hardhat, safety-vest, person classes)
Source  : Roboflow Universe — roboflow.com/universe/datasets/ppe-detection

Usage:
    python detection/download_ppe_dataset.py
"""

import zipfile
import urllib.request
import shutil
import sys
from pathlib import Path


# ── Public Ultralytics Construction-PPE Dataset URL ──────────────────────────
# Dataset: "Construction-PPE" by Ultralytics — helmet, safety-vest, gloves, etc.
DATASET_URL = (
    "https://github.com/ultralytics/assets/releases/download/v0.0.0/construction-ppe.zip"
)

DEST_DIR = Path("detection/ppe_dataset")
ZIP_FILE = Path("detection/ppe_dataset.zip")


def count_files(folder: Path, ext: str) -> int:
    return len(list(folder.rglob(f"*{ext}")))


def main():
    print("=" * 60)
    print(" Jarvis — PPE Dataset Download (Step 8)")
    print("=" * 60)

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    # ── Download ──────────────────────────────────────────────────────────────
    print(f"\n[INFO] Downloading dataset ZIP ...")
    print(f"       Source : {DATASET_URL}")
    print(f"       Saving : {ZIP_FILE}\n")

    try:
        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(downloaded / total_size * 100, 100)
                bar = int(pct / 2)
                print(f"\r  [{'#'*bar}{'-'*(50-bar)}] {pct:.1f}%", end="", flush=True)

        urllib.request.urlretrieve(DATASET_URL, ZIP_FILE, reporthook=progress)
        print(f"\n[OK]   Downloaded: {ZIP_FILE.stat().st_size / 1024 / 1024:.1f} MB")

    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        print("\n  If the URL expired, go to:")
        print("  https://universe.roboflow.com/search?q=ppe+helmet+vest")
        print("  -> Choose a dataset -> Export -> YOLOv8 -> Download ZIP")
        print(f"  -> Place the ZIP at: {ZIP_FILE}")
        sys.exit(1)

    # ── Extract ───────────────────────────────────────────────────────────────
    print(f"\n[INFO] Extracting to {DEST_DIR} ...")
    with zipfile.ZipFile(ZIP_FILE, "r") as zf:
        zf.extractall(DEST_DIR)
    ZIP_FILE.unlink()  # remove zip to save space
    print(f"[OK]   Extraction complete. ZIP removed.")

    # ── Count & report ────────────────────────────────────────────────────────
    print(f"\n--- Dataset Contents -----------------------------------------")
    total_images = count_files(DEST_DIR, ".jpg") + count_files(DEST_DIR, ".png")
    total_labels = count_files(DEST_DIR, ".txt")

    for split in ["train", "valid", "test"]:
        split_dir = DEST_DIR / split
        if split_dir.exists():
            imgs  = count_files(split_dir / "images", ".jpg") + \
                    count_files(split_dir / "images", ".png")
            lbls  = count_files(split_dir / "labels", ".txt")
            print(f"   {split:<6} | images: {imgs:>5}  | labels: {lbls:>5}")

    print(f"   {'TOTAL':<6} | images: {total_images:>5}  | labels: {total_labels:>5}")

    # Check for data.yaml (class names)
    yaml_files = list(DEST_DIR.rglob("*.yaml"))
    if yaml_files:
        print(f"\n[OK]   data.yaml found: {yaml_files[0]}")
        print("       Contents:")
        with open(yaml_files[0], encoding="utf-8") as f:
            for line in f:
                safe_line = line.encode("ascii", errors="replace").decode("ascii")
                print(f"         {safe_line}", end="")

    print(f"\n[OK]   PPE dataset ready at: {DEST_DIR.resolve()}")
    print("       Next step: custom YOLO training (not now — Step 8 is dataset only)")
    print("=" * 60)


if __name__ == "__main__":
    main()
