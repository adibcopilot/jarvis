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

    def detect(self, source: Union[str, Path, np.ndarray]) -> Dict[str, Any]:
        """
        Run Fire/Smoke detection on an image path or numpy array (BGR frame).
        """
        if isinstance(source, (str, Path)):
            src_path = Path(source)
            if not src_path.exists():
                raise FileNotFoundError(f"Image not found at: {src_path}")
            img_input = str(src_path)
        else:
            img_input = source

        results = self.model(img_input, conf=self.conf_threshold, verbose=False)
        result = results[0]

        detections = []
        hazards = []
        has_fire = False
        has_smoke = False
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

    def detect_video(self, video_path: Union[str, Path], output_path: Union[str, Path] = None) -> Dict[str, Any]:
        """
        Process a video file frame by frame with Fire/Smoke detection.
        """
        v_path = Path(video_path)
        if not v_path.exists():
            raise FileNotFoundError(f"Video file not found: {v_path}")

        cap = cv2.VideoCapture(str(v_path))
        if not cap.isOpened():
            raise IOError(f"Could not open video file: {v_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        writer = None
        if output_path:
            out_p = Path(output_path)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(out_p), fourcc, fps, (width, height))

        frame_count = 0
        total_detections = 0
        total_fire_frames = 0
        total_smoke_frames = 0
        aggregated_summary = {}

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            res = self.detect(frame)
            total_detections += len(res["detections"])
            if res["has_fire"]:
                total_fire_frames += 1
            if res["has_smoke"]:
                total_smoke_frames += 1

            for k, v in res["summary"].items():
                aggregated_summary[k] = aggregated_summary.get(k, 0) + v

            if writer:
                writer.write(res["annotated_image"])

        cap.release()
        if writer:
            writer.release()

        return {
            "frames_processed": frame_count,
            "total_detections": total_detections,
            "fire_frames": total_fire_frames,
            "smoke_frames": total_smoke_frames,
            "has_fire": total_fire_frames > 0,
            "has_smoke": total_smoke_frames > 0,
            "aggregated_summary": aggregated_summary,
            "output_path": str(output_path) if output_path else None
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test Fire/Smoke detection")
    parser.add_argument("--image", type=str, default=None, help="Path to input image")
    parser.add_argument("--video", type=str, default=None, help="Path to input video")
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

    if args.video:
        res = detector.detect_video(args.video)
        print(f"\nVideo Results for {args.video}:")
        print(f"  Frames: {res['frames_processed']}")
        print(f"  Fire Frames: {res['fire_frames']} | Smoke Frames: {res['smoke_frames']}")
        print(f"  Summary: {res['aggregated_summary']}")


if __name__ == "__main__":
    main()
