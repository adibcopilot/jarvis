"""
detection/ppe_detector.py
Core PPE Detection module using the trained YOLO model (best_ppe.pt).

Provides:
- PPEDetector: Class for image and video frame analysis
- Violation analysis (missing helmet, missing vest, etc.)
- Annotated frame generation and video processing
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

    # Set of classes representing PPE non-compliance / violations
    VIOLATION_CLASSES = {
        "no_helmet",
        "no_goggle",
        "no_gloves",
        "no_boots",
        "none",  # Represents missing vest / unequipped PPE
    }

    def __init__(self, model_path: Union[str, Path] = None, conf_threshold: float = 0.25):
        self.conf_threshold = conf_threshold
        
        # Locate model path
        if model_path is None:
            self.model_path = Path("detection/models/best_ppe.pt")
        else:
            self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found at: {self.model_path}")

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
                - violations: list of detected violations (e.g. no_helmet, no_gloves, no_boots, none)
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
            if label in self.VIOLATION_CLASSES:
                violations.append(det_item)

        annotated_image = result.plot()

        return {
            "detections": detections,
            "violations": violations,
            "has_violations": len(violations) > 0,
            "summary": summary,
            "annotated_image": annotated_image
        }

    def detect_video(self, video_path: Union[str, Path], output_path: Union[str, Path] = None) -> Dict[str, Any]:
        """
        Process a video file frame by frame with PPE detection.
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
        total_violations = 0
        aggregated_summary = {}

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            res = self.detect(frame)
            total_detections += len(res["detections"])
            total_violations += len(res["violations"])

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
            "total_violations": total_violations,
            "aggregated_summary": aggregated_summary,
            "output_path": str(output_path) if output_path else None
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test PPE detection on an image or video")
    parser.add_argument("--image", type=str, default=None, help="Path to input image")
    parser.add_argument("--video", type=str, default=None, help="Path to input video")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    args = parser.parse_args()

    # Default to sample.jpg if neither specified
    if args.image is None and args.video is None:
        args.image = "detection/test_inputs/sample.jpg"

    detector = PPEDetector(conf_threshold=args.conf)

    if args.image:
        print(f"\n[INFO] Running inference on image: {args.image}")
        res = detector.detect(args.image)

        print("\n--- Image Detection Results ---")
        print(f"Total Detections: {len(res['detections'])}")
        print(f"Summary Counts  : {res['summary']}")
        print(f"Violations Found: {len(res['violations'])}")
        for i, det in enumerate(res['detections']):
            tag = "[VIOLATION]" if det in res['violations'] else "[DETECTED] "
            print(f"  {tag} #{i+1:02d}: {det['label']:<12} conf={det['confidence']:.3f} bbox={det['bbox']}")

        out_path = Path("detection/test_inputs/sample_ppe_detected.jpg")
        cv2.imwrite(str(out_path), res["annotated_image"])
        print(f"\n[OK] Annotated image saved to: {out_path}")

    if args.video:
        print(f"\n[INFO] Running inference on video: {args.video}")
        out_video = Path("detection/test_inputs/sample_ppe_detected.mp4")
        v_res = detector.detect_video(args.video, output_path=out_video)

        print("\n--- Video Detection Results ---")
        print(f"Frames Processed : {v_res['frames_processed']}")
        print(f"Total Detections : {v_res['total_detections']}")
        print(f"Total Violations : {v_res['total_violations']}")
        print(f"Aggregated Counts: {v_res['aggregated_summary']}")
        print(f"\n[OK] Annotated video saved to: {out_video}")


if __name__ == "__main__":
    main()
