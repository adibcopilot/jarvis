"""
detection/ppe_detector.py
Core PPE Detection module using the trained YOLO model (best_ppe.pt).

Provides:
- PPEDetector: Class for image and video frame analysis
- Violation analysis (missing helmet, missing vest, etc.)
- Annotated frame generation
"""

from pathlib import Path
from typing import List, Dict, Any, Union
import cv2
import numpy as np
from ultralytics import YOLO


class PPEDetector:
    """
    YOLO-based detector for Personal Protective Equipment (PPE) compliance.
    Default model: models/best_ppe.pt or detection/models/best_ppe.pt
    """

    def __init__(self, model_path: Union[str, Path] = None, conf_threshold: float = 0.25):
        self.conf_threshold = conf_threshold
        
        # Locate model path
        if model_path is None:
            candidates = [
                Path("detection/models/best_ppe.pt"),
                Path("models/best_ppe.pt"),
                Path("yolo26n.pt"),
            ]
            for c in candidates:
                if c.exists():
                    self.model_path = c
                    break
            else:
                self.model_path = Path("detection/models/best_ppe.pt")
        else:
            self.model_path = Path(model_path)

        print(f"[INFO] Initializing PPEDetector with model: {self.model_path}")
        self.model = YOLO(str(self.model_path))
        self.classes = self.model.names
        print(f"[OK]   Model loaded successfully. Classes ({len(self.classes)}): {self.classes}")

    def detect(self, image_or_frame: Union[str, Path, np.ndarray]) -> Dict[str, Any]:
        """
        Run PPE detection on an image path or numpy frame.
        
        Returns:
            dict containing:
                - detections: list of bounding boxes, labels, and confidences
                - violations: list of detected violations (e.g. no_helmet, no_gloves, no_boots)
                - summary: counts of each detected class
                - annotated_image: numpy BGR image with plotted bounding boxes
        """
        results = self.model(image_or_frame, conf=self.conf_threshold, verbose=False)
        result = results[0]
        
        detections = []
        violations = []
        summary = {}

        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            label = self.classes.get(cls_id, str(cls_id))
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]

            det_item = {
                "class_id": cls_id,
                "label": label,
                "confidence": round(conf, 3),
                "bbox": [x1, y1, x2, y2]
            }
            detections.append(det_item)
            summary[label] = summary.get(label, 0) + 1

            # Check if this detection indicates a violation
            if label.startswith("no_") or label in ["no_helmet", "no_goggle", "no_gloves", "no_boots"]:
                violations.append(det_item)

        annotated_image = result.plot()

        return {
            "detections": detections,
            "violations": violations,
            "has_violations": len(violations) > 0,
            "summary": summary,
            "annotated_image": annotated_image
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test PPE detection on an image or video")
    parser.add_argument("--image", type=str, default="detection/test_inputs/sample.jpg", help="Path to input image")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    args = parser.parse_args()

    detector = PPEDetector(conf_threshold=args.conf)
    res = detector.detect(args.image)

    print("\n--- Detection Results ---")
    print(f"Total Detections: {len(res['detections'])}")
    print(f"Summary Counts : {res['summary']}")
    print(f"Violations Found: {len(res['violations'])}")
    for v in res['violations']:
        print(f"  [VIOLATION] {v['label']} (conf: {v['confidence']}) at {v['bbox']}")

    out_path = Path("detection/test_inputs/sample_ppe_detected.jpg")
    cv2.imwrite(str(out_path), res["annotated_image"])
    print(f"\n[OK] Annotated output saved to: {out_path}")


if __name__ == "__main__":
    main()
