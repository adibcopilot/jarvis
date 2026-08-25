import ultralytics
print("ultralytics version:", ultralytics.__version__)

from ultralytics import YOLO
print("Attempting: YOLO('yolo26n.pt') ...")
try:
    model = YOLO("yolo26n.pt")
    print("[OK] yolo26n.pt loaded! Task:", model.task, "| Classes:", len(model.names))
except Exception as e:
    print("[ERROR]", type(e).__name__, "-", e)
