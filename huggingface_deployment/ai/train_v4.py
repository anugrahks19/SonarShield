import os
from ultralytics import YOLO

def main():
    print("Starting V4: HIGH-RESOLUTION HARD POSITIVE MINING EXPERIMENT")
    
    # Start from base YOLOv8s Checkpoint (clean baseline comparison)
    model = YOLO("yolov8s.pt")
    
    # V4 Dataset Target (V3 + Multi-scale Hard Positives)
    data_yaml = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v4\drishti_v4.yaml"
    
    # Train (imgsz=960, batch=8 as requested)
    model.train(
        data=data_yaml,
        epochs=50,
        patience=10,
        batch=8,
        imgsz=960,
        project=r"E:\GITHUB\a sih 2026\models\v4",
        name="detector_v4",
        device=0,
        workers=0
    )

if __name__ == "__main__":
    main()
