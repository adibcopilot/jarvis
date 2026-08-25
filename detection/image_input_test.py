"""
detection/image_input_test.py
Step 3 — Load and display a static image using OpenCV.
No AI. Just proves cv2.imread + cv2.imshow work.
Press 'q' to close.

Usage:
    python detection/image_input_test.py
    python detection/image_input_test.py --image detection/test_inputs/sample.jpg
"""

import argparse
import sys
import cv2
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=str,
                        default="detection/test_inputs/sample.jpg",
                        help="Path to the image file")
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"[ERROR] Image not found: {img_path}")
        print("        Run detection/download_test_assets.py first.")
        sys.exit(1)

    frame = cv2.imread(str(img_path))
    if frame is None:
        print(f"[ERROR] cv2.imread() returned None for: {img_path}")
        sys.exit(1)

    h, w, c = frame.shape
    print(f"[OK]  Image loaded: {img_path}")
    print(f"      Size     : {w}x{h}  |  Channels: {c}")
    print("[INFO] Window opened. Press 'q' to quit.")

    # Stamp filename on the image
    cv2.putText(frame, str(img_path.name),
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.9, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.putText(frame, f"{w}x{h}",
                (10, 65), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 200, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, "Press 'q' to quit",
                (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (120, 120, 120), 1, cv2.LINE_AA)

    cv2.imshow("JARVIS — Image Input Test", frame)

    while True:
        key = cv2.waitKey(0) & 0xFF
        if key == ord('q') or key == 27:   # q or Esc
            break

    cv2.destroyAllWindows()
    print("[DONE] Window closed.")


if __name__ == "__main__":
    main()
