"""
detection/run_tests.py
Script to run dedicated tests on both PPE and Fire/Smoke detection systems.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from detection.ppe_detector import PPEDetector
from detection.fire_detector import FireSmokeDetector


def test_ppe():
    print("=" * 75)
    print(" 1. PPE DETECTION SYSTEM TEST")
    print("=" * 75)
    
    ppe_detector = PPEDetector(conf_threshold=0.25)
    ppe_dir = Path("detection/test_inputs/ppe")
    ppe_images = sorted([
        p for p in ppe_dir.glob("*.*")
        if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
        and not any(tag in p.stem for tag in ["_boxed", "_detected"])
    ])
    
    print(f"\nModel File   : {ppe_detector.model_path}")
    print(f"Model Classes: {ppe_detector.classes}")
    print(f"Testing {len(ppe_images)} PPE image(s) from {ppe_dir}\n")
    
    results = []
    
    for idx, img_p in enumerate(ppe_images, start=1):
        res = ppe_detector.detect(img_p)
        dets = res["detections"]
        viols = res["violations"]
        
        print(f"[{idx:02d}/{len(ppe_images):02d}] Image: {img_p.name}")
        if not dets:
            print("       Detections: NONE")
            print("       Violations: 0")
        else:
            print(f"       Detections ({len(dets)}):")
            for d in dets:
                tag = "[VIOLATION]" if d in viols else "[DETECTED] "
                print(f"         {tag} {d['label']:<12} conf={d['confidence']:.3f} bbox={d['bbox']}")
            print(f"       Violations ({len(viols)}): {[v['label'] for v in viols]}")
        print()
        results.append((img_p.name, dets, viols))
        
    return results


def test_fire_smoke():
    print("=" * 75)
    print(" 2. FIRE & SMOKE DETECTION SYSTEM TEST")
    print("=" * 75)
    
    fire_detector = FireSmokeDetector(conf_threshold=0.25)
    fire_dir = Path("detection/test_inputs/fire_smoke")
    fire_images = sorted([
        p for p in fire_dir.glob("*.*")
        if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
        and not any(tag in p.stem for tag in ["_boxed", "_detected"])
    ])
    
    print(f"\nModel File   : {fire_detector.model_path}")
    print(f"Model Classes: {fire_detector.classes}")
    print(f"Testing {len(fire_images)} Fire/Smoke image(s) from {fire_dir}\n")
    
    for idx, img_p in enumerate(fire_images, start=1):
        res = fire_detector.detect(img_p)
        dets = res["detections"]
        
        print(f"[{idx:02d}/{len(fire_images):02d}] Image: {img_p.name}")
        print(f"       Has Fire : {res['has_fire']}")
        print(f"       Has Smoke: {res['has_smoke']}")
        if not dets:
            print("       Detections: NONE")
        else:
            print(f"       Detections ({len(dets)}):")
            for d in dets:
                print(f"         - {d['label']:<15} conf={d['confidence']:.3f} bbox={d['bbox']}")
        print()

    # Control non-fire image test
    control_img = Path("detection/test_inputs/ppe/helmet.jpg")
    if control_img.exists():
        print(f"[CONTROL NON-FIRE TEST] Image: {control_img.name}")
        c_res = fire_detector.detect(control_img)
        print(f"       Has Fire : {c_res['has_fire']}")
        print(f"       Has Smoke: {c_res['has_smoke']}")
        print(f"       Detections: {c_res['summary']}")
        print()


def main():
    test_ppe()
    test_fire_smoke()


if __name__ == "__main__":
    main()
