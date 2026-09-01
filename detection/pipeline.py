"""
detection/pipeline.py
Unified detection & simulation pipeline: runs the correct model or simulator, logs to SQLite, classifies with the agent.

Usage:
    from detection.pipeline import run_ppe_pipeline, run_fire_pipeline, run_conveyor_fault_pipeline
    event_id = run_ppe_pipeline("path/to/image.jpg")
    event_id = run_fire_pipeline("path/to/image.jpg")
    event_id = run_conveyor_fault_pipeline("jam")
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from detection.ppe_detector import PPEDetector
from detection.fire_detector import FireSmokeDetector
from simulation.conveyor import trigger_fault, is_commanded_change, get_status
from database.db import insert_event
from agent.reasoner import classify_event


# Lazy-loaded singletons so the model only loads once
_ppe_detector = None
_fire_detector = None


def _get_ppe_detector():
    global _ppe_detector
    if _ppe_detector is None:
        _ppe_detector = PPEDetector()
    return _ppe_detector


def _get_fire_detector():
    global _fire_detector
    if _fire_detector is None:
        _fire_detector = FireSmokeDetector()
    return _fire_detector


def run_ppe_pipeline(image_path: str) -> dict:
    """
    Full PPE pipeline: detect -> classify -> log to database.
    Returns dict with event_id, detections, classification, and annotated_image.
    """
    detector = _get_ppe_detector()
    result = detector.detect(image_path)

    # Run reasoning agent
    classification = classify_event("ppe", result["detections"], source_file=str(image_path))

    # Log to database
    event_id = insert_event(
        event_type="ppe",
        source_file=str(Path(image_path).name),
        detections=result["detections"],
        severity=classification["severity"],
        category=classification["category"],
        proposed_action=classification["proposed_action"],
    )

    return {
        "event_id": event_id,
        "detections": result["detections"],
        "violations": result["violations"],
        "has_violations": result["has_violations"],
        "summary": result["summary"],
        "classification": classification,
        "annotated_image": result["annotated_image"],
    }


def run_fire_pipeline(image_path: str) -> dict:
    """
    Full Fire/Smoke pipeline: detect -> classify -> log to database.
    Returns dict with event_id, detections, classification, and annotated_image.
    """
    detector = _get_fire_detector()
    result = detector.detect(image_path)

    # Run reasoning agent
    classification = classify_event("fire", result["detections"], source_file=str(image_path))

    # Log to database
    event_id = insert_event(
        event_type="fire",
        source_file=str(Path(image_path).name),
        detections=result["detections"],
        severity=classification["severity"],
        category=classification["category"],
        proposed_action=classification["proposed_action"],
    )

    return {
        "event_id": event_id,
        "detections": result["detections"],
        "has_fire": result["has_fire"],
        "has_smoke": result["has_smoke"],
        "summary": result["summary"],
        "classification": classification,
        "annotated_image": result["annotated_image"],
    }


def run_conveyor_fault_pipeline(fault_type: str = "mechanical_jam") -> dict:
    """
    Full Conveyor Fault pipeline: trigger fault -> classify -> log to database.
    Returns dict with event_id, conveyor_status, and classification.
    """
    status_info = trigger_fault(fault_type=fault_type)
    commanded = is_commanded_change()

    # Run reasoning agent
    classification = classify_event(
        "conveyor",
        source_file=f"Conveyor Line {status_info['line_id']}",
        extra_data={"status": status_info["status"], "commanded": commanded, "fault_type": fault_type}
    )

    # Log to database
    event_id = insert_event(
        event_type="conveyor",
        source_file=f"Conveyor Line {status_info['line_id']} ({fault_type})",
        detections=[{"label": "conveyor_fault", "fault_type": fault_type, "confidence": 1.0}],
        severity=classification["severity"],
        category=classification["category"],
        proposed_action=classification["proposed_action"],
    )

    return {
        "event_id": event_id,
        "conveyor_status": status_info,
        "classification": classification,
    }
