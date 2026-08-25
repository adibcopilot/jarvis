"""
detection/yolo_download_test.py
Step 3 & 4 — Download yolov8n.pt and run it on a test image.

Usage:
    python detection/yolo_download_test.py                        # uses built-in test image
    python detection/yolo_download_test.py --image path/to/img.jpg
"""

import argparse
import urllib.request
from pathlib import Path
from ultralytics import YOLO


# ── Helpers ─────────────────────────────────────────────────────────────────

def download_sample_image(dest: Path) -> Path:
    """Download a sample street photo with people from Unsplash (free)."""
    url = "https://ultralytics.com/images/bus.jpg"  # official YOLO test image
    print(f"[INFO] Downloading sample test image from {url} ...")
    urllib.request.urlretrieve(url, dest)
    print(f"[OK]   Saved to {dest}")
    return dest


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=str, default=None,
                        help="Path to a test image (optional — defaults to bus.jpg)")
    args = parser.parse_args()

    # Step 3: Load / download model
    print("\n── Step 3: Loading YOLOv8n model ──────────────────────────────")
    print("[INFO] If yolo26n.pt is not found locally, Ultralytics will auto-download it (~5.3MB).")
    model = YOLO("yolo26n.pt")
    print(f"[OK]   Model loaded: {type(model)}")
    print(f"       Task         : {model.task}")
    print(f"       Classes      : {len(model.names)} COCO classes")

    # Step 4: Run inference on image
    print("\n── Step 4: Running inference on test image ─────────────────────")
    if args.image:
        img_path = Path(args.image)
        if not img_path.exists():
            print(f"[ERROR] Image not found: {img_path}")
            return
    else:
        img_path = Path("detection/test_image.jpg")
        if not img_path.exists():
            download_sample_image(img_path)

    print(f"[INFO] Running YOLO on: {img_path}")
    results = model(str(img_path))

    result = results[0]
    boxes = result.boxes
    print(f"\n[OK]   Detection complete!")
    print(f"       Detections   : {len(boxes)}")

    if len(boxes) > 0:
        for i, box in enumerate(boxes):
            cls_id  = int(box.cls[0])
            conf    = float(box.conf[0])
            label   = model.names[cls_id]
            x1,y1,x2,y2 = [int(v) for v in box.xyxy[0]]
            print(f"       [{i+1}] {label:15s} conf={conf:.2f}  bbox=({x1},{y1})-({x2},{y2})")
    else:
        print("       [WARN] No objects detected. Try a different image.")

    # Save the annotated output
    output_path = Path("detection/test_output.jpg")
    result.save(filename=str(output_path))
    print(f"\n[OK]   Annotated image saved → {output_path}")
    print("       Open it to confirm bounding boxes are drawn.\n")


if __name__ == "__main__":
    main()
