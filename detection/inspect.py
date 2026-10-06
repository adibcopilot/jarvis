"""
Upload & Inspect pipeline.

Tries YOLO perception when weights are present. Otherwise runs a labeled
software-simulation of PPE or fire/smoke inspection so the web demo still
logs events, classifies severity, and queues human approval.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.db import insert_event, get_all_workers
from agent.reasoner import classify_event

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

SAMPLE_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf"
    b"\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)

WORKER_HINTS = [
    ("miller", "W-8472"),
    ("sarah", "W-8472"),
    ("lopez", "W-1044"),
    ("marcus", "W-1044"),
    ("sharma", "W-510"),
    ("priya", "W-510"),
    ("kapoor", "W-441"),
    ("nina", "W-441"),
    ("sagar", "W-102"),
    ("rudra", "W-102"),
    ("rostova", "W-305"),
    ("elena", "W-305"),
    ("kim", "W-402"),
    ("davis", "W-9211"),
    ("bradley", "W-330"),
    ("chen", "W-718"),
]


def save_upload(filename: str, data: bytes) -> Path:
    safe_name = Path(filename).name.replace(" ", "_")
    dest = UPLOAD_DIR / safe_name
    dest.write_bytes(data)
    return dest


def run_demo_inspection(inspection_type: str) -> Dict[str, Any]:
    kind = _normalize_type(inspection_type)
    filename = "sample_ppe_missing_helmet.png" if kind == "ppe" else "sample_fire_sector4.png"
    saved = save_upload(filename, SAMPLE_PNG)
    return run_inspection(kind, saved, filename)


def run_inspection(inspection_type: str, file_path: Path, original_name: str) -> Dict[str, Any]:
    """Run PPE or fire inspection on an uploaded file and log the event."""
    kind = _normalize_type(inspection_type)
    yolo = _try_real_pipeline(kind, file_path)
    if yolo:
        return yolo
    return _run_simulated(kind, original_name)


def _normalize_type(inspection_type: str) -> str:
    value = (inspection_type or "ppe").strip().lower()
    if value in ("fire", "smoke", "fire_smoke", "fire-smoke", "hazard"):
        return "fire"
    return "ppe"


def _try_real_pipeline(kind: str, file_path: Path) -> Optional[Dict[str, Any]]:
    model_name = "best_ppe.pt" if kind == "ppe" else "best_fire.pt"
    model_path = ROOT_DIR / "detection" / "models" / model_name
    if not model_path.exists():
        return None
    try:
        from detection.pipeline import run_ppe_pipeline, run_fire_pipeline
        result = run_ppe_pipeline(str(file_path)) if kind == "ppe" else run_fire_pipeline(str(file_path))
        cls = result.get("classification") or {}
        return {
            "success": True,
            "mode": "yolo",
            "inspection_type": kind,
            "event_id": result.get("event_id"),
            "detections": result.get("detections") or [],
            "violations": result.get("violations") or [],
            "has_violations": result.get("has_violations", False),
            "summary": result.get("summary") or {},
            "severity": cls.get("severity", "pending"),
            "category": cls.get("category", "safety"),
            "proposed_action": cls.get("proposed_action", ""),
            "reasoning": cls.get("reasoning", ""),
            "note": "YOLO perception layer produced this inspection result.",
        }
    except Exception:
        return None


def _match_worker(filename: str) -> Optional[Dict[str, Any]]:
    lower = filename.lower()
    workers = {w.get("worker_code"): w for w in get_all_workers()}
    for hint, code in WORKER_HINTS:
        if hint in lower and code in workers:
            return workers[code]
    # Cycle a flagged/probation worker for unnamed PPE uploads so records stay attributable
    for w in workers.values():
        if (w.get("status") or "").lower() in ("probation", "flagged"):
            return w
    return next(iter(workers.values()), None)


def _simulate_detections(kind: str, filename: str) -> List[Dict[str, Any]]:
    name = filename.lower()
    worker = _match_worker(filename) if kind == "ppe" else None
    worker_code = worker.get("worker_code") if worker else None
    worker_name = worker.get("name") if worker else None

    if kind == "fire":
        if any(k in name for k in ("clear", "ok", "none", "compliant", "safe")):
            return []
        if "smoke" in name and "fire" not in name:
            return [{"label": "smoke", "class": "smoke", "confidence": 0.84, "location": "uploaded feed"}]
        if "smoke" in name:
            return [
                {"label": "fire", "class": "fire", "confidence": 0.91, "location": "uploaded feed"},
                {"label": "smoke", "class": "smoke", "confidence": 0.88, "location": "uploaded feed"},
            ]
        return [{"label": "fire", "class": "fire", "confidence": 0.93, "location": "uploaded feed"}]

    detections: List[Dict[str, Any]] = [
        {
            "label": "Person",
            "class": "person",
            "confidence": 0.92,
            "worker_code": worker_code,
            "worker_name": worker_name,
        }
    ]
    if any(k in name for k in ("clear", "ok", "compliant", "safe")):
        detections.extend([
            {"label": "helmet", "confidence": 0.90},
            {"label": "vest", "confidence": 0.88},
        ])
        return detections

    missing = []
    if "goggle" in name or "eye" in name:
        missing.append("no_goggle")
    if "glove" in name:
        missing.append("no_gloves")
    if "boot" in name:
        missing.append("no_boots")
    if "vest" in name:
        missing.append("none")
    if "helmet" in name or "hardhat" in name:
        missing.append("no_helmet")
    if not missing:
        missing = ["no_helmet", "none"]

    for label in missing:
        detections.append({
            "label": label,
            "class": label,
            "confidence": 0.86,
            "worker_code": worker_code,
            "worker_name": worker_name,
        })
    return detections


def _run_simulated(kind: str, original_name: str) -> Dict[str, Any]:
    detections = _simulate_detections(kind, original_name)
    classification = classify_event(kind, detections, source_file=original_name)
    event_id = insert_event(
        event_type=kind,
        source_file=original_name,
        detections=detections,
        severity=classification.get("severity", "pending"),
        category=classification.get("category", "safety"),
        proposed_action=classification.get("proposed_action", ""),
    )
    violations = [d for d in detections if str(d.get("label", "")).startswith("no") or d.get("label") in ("none", "fire", "smoke")]
    worker = _match_worker(original_name) if kind == "ppe" else None
    return {
        "success": True,
        "mode": "simulated",
        "inspection_type": kind,
        "event_id": event_id,
        "detections": detections,
        "violations": violations,
        "has_violations": bool(violations),
        "summary": {d.get("label"): 1 for d in detections},
        "severity": classification.get("severity", "pending"),
        "category": classification.get("category", "safety"),
        "proposed_action": classification.get("proposed_action", ""),
        "reasoning": classification.get("reasoning", ""),
        "worker": {
            "worker_code": worker.get("worker_code"),
            "name": worker.get("name"),
        } if worker else None,
        "note": "YOLO weights are not loaded. Inspection used the software-simulation perception layer and logged a live event for approval.",
    }
