"""
detection/fire_detector.py
Fire and Smoke Detection module using the trained YOLO model (best_fire.pt).

Provides:
- FireSmokeDetector: Class for analyzing fire/smoke in images and video frames
- Hazard alerts (fire, smoke)
- Annotated frame generation
"""

from pathlib import Path
from typing import List, Dict, Any, Union
import cv2
import numpy as np
from ultralytics import YOLO


class FireSmokeDetector:
    """
    YOLO-based detector for Fire and Smoke hazards.
    Default model: detection/models/best_fire.pt
    """

    HAZARD_CLASSES = {"fire", "smoke"}

    def __init__(self, model_path: Union[str, Path] = None, conf_threshold: float = 0.25):
        self.conf_threshold = conf_threshold

        if model_path is None:
            self.model_path = Path("detection/models/best_fire.pt")
        else:
            self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found at: {self.model_path}")

        print(f"[INFO] Initializing FireSmokeDetector with model: {self.model_path}")
        self.model = YOLO(str(self.model_path))
        self.classes = self.model.names
        print(f"[OK]   Fire/Smoke model loaded. Classes ({len(self.classes)}): {self.classes}")

    def detect(self, image_or_frame: Union[str, Path, np.ndarray]) -> Dict[str, Any]:
        """
        Run Fire & Smoke detection on an image path or numpy frame.
        
        Returns:
            dict containing:
                - detections: list of all detected bounding boxes
                - hazards: list of fire / smoke detections specifically
                - has_fire: bool
                - has_smoke: bool
                - summary: frequency counts of each class
                - annotated_image: numpy BGR image with plotted bounding boxes
        """
        results = self.model(image_or_frame, conf=self.conf_threshold, verbose=False)
        result = results[0]

        detections = []
        hazards = []
        summary = {}

        has_fire = False
        has_smoke = False

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

            if label.lower() == "fire":
                has_fire = True
                hazards.append(det_item)
            elif label.lower() == "smoke":
                has_smoke = True
                hazards.append(det_item)

        annotated_image = result.plot()

        return {
            "detections": detections,
            "hazards": hazards,
            "has_fire": has_fire,
            "has_smoke": has_smoke,
            "has_hazards": len(hazards) > 0,
            "summary": summary,
            "annotated_image": annotated_image
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test Fire/Smoke detection")
    parser.add_argument("--image", type=str, default=None, help="Path to input image")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    args = parser.parse_args()

    detector = FireSmokeDetector(conf_threshold=args.conf)

    if args.image:
        res = detector.detect(args.image)
        print(f"\nResults for {args.image}:")
        print(f"  Summary: {res['summary']}")
        print(f"  Has Fire: {res['has_fire']} | Has Smoke: {res['has_smoke']}")
        for d in res['detections']:
            print(f"  - {d['label']} (conf: {d['confidence']}) at {d['bbox']}")


if __name__ == "__main__":
    main()
