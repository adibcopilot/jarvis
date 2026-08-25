"""
detection/yolo_video_test.py
Step 7 — Run YOLOv8 detection on every frame of a video file.

Reads sample.mp4 frame by frame, runs YOLO inference on each,
draws bounding boxes, plays the result in a window.
No webcam. No live camera feed.

Press 'q' to quit, 'p' to pause/resume.

Usage:
    python detection/yolo_video_test.py
    python detection/yolo_video_test.py --video detection/test_inputs/sample.mp4
    python detection/yolo_video_test.py --video path/to/video.mp4 --conf 0.4
    python detection/yolo_video_test.py --save   # also writes boxed video to disk
"""

import argparse
import sys
import time
from pathlib import Path
import cv2
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str,
                        default="detection/test_inputs/sample.mp4")
    parser.add_argument("--model", type=str, default="yolo26n.pt")
    parser.add_argument("--conf",  type=float, default=0.35)
    parser.add_argument("--save",  action="store_true",
                        help="Also save annotated video to disk")
    args = parser.parse_args()

    vid_path = Path(args.video)
    if not vid_path.exists():
        print(f"[ERROR] Video not found: {vid_path}")
        sys.exit(1)

    # ── Load model ────────────────────────────────────────────────────────────
    print(f"[INFO] Loading {args.model} …")
    model = YOLO(args.model)
    print(f"[OK]   Model ready | {len(model.names)} COCO classes")

    # ── Open video file ───────────────────────────────────────────────────────
    cap = cv2.VideoCapture(str(vid_path))
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {vid_path}")
        sys.exit(1)

    fps_src = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total   = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    delay   = max(1, int(1000 / fps_src))

    print(f"[OK]   Video: {vid_path.name}  |  {w}x{h}  |  {fps_src:.0f}fps  |  {total} frames")
    print("[INFO] Press 'q' to quit, 'p' to pause.\n")

    # ── Optional output writer ────────────────────────────────────────────────
    writer = None
    if args.save:
        out_path = vid_path.parent / (vid_path.stem + "_boxed.mp4")
        fourcc   = cv2.VideoWriter_fourcc(*"mp4v")
        writer   = cv2.VideoWriter(str(out_path), fourcc, fps_src, (w, h))
        print(f"[INFO] Saving annotated video to: {out_path}")

    frame_idx  = 0
    paused     = False
    total_dets = 0
    t_start    = time.time()

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print(f"\n[INFO] End of video after {frame_idx} frames.")
                break

            frame_idx += 1

            # ── YOLO inference ────────────────────────────────────────────────
            results  = model(frame, conf=args.conf, verbose=False)
            annotated = results[0].plot()          # draws boxes on copy of frame
            n_det     = len(results[0].boxes)
            total_dets += n_det

            # ── HUD ───────────────────────────────────────────────────────────
            elapsed = time.time() - t_start
            avg_fps = frame_idx / max(elapsed, 0.001)

            cv2.putText(annotated, f"Frame {frame_idx}/{total}",
                        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(annotated, f"Detections: {n_det}  |  Avg FPS: {avg_fps:.1f}",
                        (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2)
            cv2.putText(annotated, f"Model: {args.model}  conf≥{args.conf}",
                        (10, 86), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

            # Progress bar
            prog = frame_idx / max(total, 1)
            cv2.rectangle(annotated, (10, h-18), (w-10, h-8), (50,50,50), -1)
            cv2.rectangle(annotated, (10, h-18),
                          (10+int((w-20)*prog), h-8), (0, 200, 100), -1)
            cv2.putText(annotated, "q=quit  p=pause",
                        (10, h-22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150,150,150), 1)

            cv2.imshow("JARVIS — YOLO Video Detection", annotated)

            if writer:
                writer.write(annotated)

        key = cv2.waitKey(delay) & 0xFF
        if key == ord('q') or key == 27:
            print(f"\n[OK]  Quit at frame {frame_idx}.")
            break
        elif key == ord('p'):
            paused = not paused
            print(f"[INFO] {'Paused' if paused else 'Resumed'}")

    # ── Cleanup & summary ─────────────────────────────────────────────────────
    cap.release()
    if writer:
        writer.release()
        print(f"[OK]  Annotated video saved.")
    cv2.destroyAllWindows()

    elapsed = time.time() - t_start
    print(f"\n── Summary ─────────────────────────────────────────────────────")
    print(f"   Frames processed : {frame_idx}")
    print(f"   Total detections : {total_dets}")
    print(f"   Avg detections/f : {total_dets/max(frame_idx,1):.1f}")
    print(f"   Elapsed time     : {elapsed:.1f}s")
    print(f"   Avg FPS          : {frame_idx/max(elapsed,0.001):.1f}")
    print("[DONE]")


if __name__ == "__main__":
    main()
