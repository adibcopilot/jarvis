"""
detection/video_input_test.py
Step 4 — Read and play a video file frame-by-frame using OpenCV.
NO webcam. No AI. Just proves cv2.VideoCapture(file) works.
Press 'q' to quit, 'p' to pause/resume.

Usage:
    python detection/video_input_test.py
    python detection/video_input_test.py --video detection/test_inputs/sample.mp4
"""

import argparse
import sys
import time
import cv2
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str,
                        default="detection/test_inputs/sample.mp4",
                        help="Path to the video file")
    args = parser.parse_args()

    vid_path = Path(args.video)
    if not vid_path.exists():
        print(f"[ERROR] Video not found: {vid_path}")
        print("        Run detection/download_test_assets.py first.")
        sys.exit(1)

    cap = cv2.VideoCapture(str(vid_path))
    if not cap.isOpened():
        print(f"[ERROR] cv2.VideoCapture could not open: {vid_path}")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_src      = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w            = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h            = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    delay_ms     = max(1, int(1000 / fps_src))

    print(f"[OK]  Video opened  : {vid_path}")
    print(f"      Resolution    : {w}x{h}")
    print(f"      FPS (source)  : {fps_src:.1f}")
    print(f"      Total frames  : {total_frames}")
    print("[INFO] Playing in window. Press 'q' to quit, 'p' to pause/resume.\n")

    frame_idx = 0
    paused    = False

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print(f"[INFO] Video ended after {frame_idx} frames. Rewinding...")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_idx = 0
                continue

            frame_idx += 1

            # HUD
            progress = frame_idx / max(total_frames, 1)
            cv2.putText(frame, f"{vid_path.name}",
                        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Frame {frame_idx}/{total_frames}  |  {fps_src:.0f} fps",
                        (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1)

            # Progress bar
            bar_w = w - 20
            cv2.rectangle(frame, (10, h - 18), (10 + bar_w, h - 8),
                          (60, 60, 60), -1)
            cv2.rectangle(frame, (10, h - 18),
                          (10 + int(bar_w * progress), h - 8),
                          (0, 200, 100), -1)
            cv2.putText(frame, "q=quit  p=pause",
                        (10, h - 22), cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, (180, 180, 180), 1)

            cv2.imshow("JARVIS — Video Input Test", frame)

        key = cv2.waitKey(delay_ms) & 0xFF
        if key == ord('q') or key == 27:
            print(f"[OK]  Quit at frame {frame_idx}.")
            break
        elif key == ord('p'):
            paused = not paused
            print(f"[INFO] {'Paused' if paused else 'Resumed'}")

    cap.release()
    cv2.destroyAllWindows()
    print("[DONE] Video playback finished cleanly.")


if __name__ == "__main__":
    main()
