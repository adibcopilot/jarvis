"""
detection/yolo_image_test.py
Step 5 & 6 — Download yolo26n.pt and run it on the sample image.

Auto-downloads yolo26n.pt (~5.3 MB) on first run via Ultralytics.
Saves annotated output to detection/test_inputs/sample_boxed.jpg.

NOTE: Pretrained COCO weights detect 80 general classes (person, car,
bottle, etc.) — NOT helmet or vest. That requires custom training later.
This is expected and NOT a bug.

Usage:
    python detection/yolo_image_test.py
    python detection/yolo_image_test.py --image detection/test_inputs/sample.jpg
"""

import argparse
import sys
import cv2
from pathlib import Path
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=str,
                        default="detection/test_inputs/sample.jpg")
    parser.add_argument("--conf",  type=float, default=0.35,
                        help="Confidence threshold (default 0.35)")
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"[ERROR] Image not found: {img_path}")
        sys.exit(1)

    # ── Step 5: Load / download model ────────────────────────────────────────
    print("\n── Step 5: Loading yolo26n.pt ──────────────────────────────────")
    print("[INFO] First run will auto-download (~5.3 MB) …")
    model = YOLO("yolo26n.pt")
    print(f"[OK]   Model loaded  | Task: {model.task} | Classes: {len(model.names)}")

    # ── Step 6: Run inference ────────────────────────────────────────────────
    print(f"\n── Step 6: Running YOLO on {img_path} ─────────────────────────")
    results = model(str(img_path), conf=args.conf)
    result  = results[0]
    boxes   = result.boxes

    print(f"[OK]   Detections : {len(boxes)}")
    if len(boxes) == 0:
        print("[WARN] No objects detected — try lowering --conf or use a different image.")
    else:
        for i, box in enumerate(boxes):
            cls_id       = int(box.cls[0])
            conf         = float(box.conf[0])
            label        = model.names[cls_id]
            x1,y1,x2,y2 = [int(v) for v in box.xyxy[0]]
            print(f"       [{i+1:2d}] {label:15s}  conf={conf:.2f}  "
                  f"bbox=({x1},{y1})→({x2},{y2})")

    # ── Save annotated output ─────────────────────────────────────────────────
    out_path = img_path.parent / (img_path.stem + "_boxed" + img_path.suffix)
    annotated = result.plot()                    # returns BGR numpy array
    cv2.imwrite(str(out_path), annotated)
    print(f"\n[OK]   Annotated image saved → {out_path}")
    print("       Open that file to confirm bounding boxes are drawn.\n")

    # Also show in a window
    print("[INFO] Showing annotated image. Press any key to close.")
    cv2.imshow("JARVIS — YOLO Image Detection", annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    print("[DONE]")


if __name__ == "__main__":
    main()
