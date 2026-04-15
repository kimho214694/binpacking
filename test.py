import cv2, numpy as np, torch
from ultralytics import YOLO

print("OpenCV:", cv2.__version__)
print("PyTorch:", torch.__version__)
model = YOLO('yolov8n.pt')
print("정상!")