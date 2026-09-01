"""
detection/test_all_inputs.py
Batch test runner for all input images and videos in detection/test_inputs/
"""

import sys
from pathlib import Path

# Ensure jarvis root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import cv2
from detection.ppe_detector import PPEDetector


def main():
    detector = PPEDetector(conf_threshold=0.25)
    input_dir = Path("detection/test_inputs")

    # Find all original test images
    images = [
        p for p in input_dir.glob("*.*")
        if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
        and not any(tag in p.stem for tag in ["_boxed", "_detected"])
    ]

    print(f"\n=======================================================")
    print(f" Found {len(images)} Input Image(s) in {input_dir}")
    print(f"=======================================================\n")

    for idx, img_path in enumerate(sorted(images), start=1):
        print("-" * 65)
        print(f"[{idx}/{len(images)}] Input: {img_path.name}")
        print("-" * 65)

        res = detector.detect(img_path)
        det_list = res["detections"]
        viol_list = res["violations"]

        print(f"Total Detections : {len(det_list)}")
        print(f"Summary Counts   : {res['summary']}")
        print(f"Violations Found : {len(viol_list)}")

        if det_list:
            for i, det in enumerate(det_list, start=1):
                is_viol = det in viol_list
                tag = "[VIOLATION]" if is_viol else "[DETECTED] "
                print(f"  {tag} #{i:02d}: {det['label']:<12} (conf: {det['confidence']:.3f}) bbox: {det['bbox']}")
        else:
            print("  [INFO] No PPE/Person classes detected in this image.")

        # Save annotated image
        out_file = input_dir / f"{img_path.stem}_ppe_detected{img_path.suffix}"
        cv2.imwrite(str(out_file), res["annotated_image"])
        print(f"[OK] Saved annotated image -> {out_file.name}\n")


if __name__ == "__main__":
    main()
