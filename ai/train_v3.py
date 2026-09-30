import os
from ultralytics import YOLO

def main():
    print("Starting V3: TARGETED DATA REFINEMENT EXPERIMENT")
    
    # 1. Start from base YOLOv8s Checkpoint
    model = YOLO("yolov8s.pt")
    
    # 2. V3 Dataset Target
    data_yaml = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\drishti_v3.yaml"
    
    # 3. Train (matching V1 config exactly)
    model.train(
        data=data_yaml,
        epochs=50,
        patience=10,
        batch=16,
        imgsz=640,
        project=r"E:\GITHUB\a sih 2026\models\v3",
        name="detector_v3",
        device=0,
        workers=0  # Keeping this to prevent the Windows multiprocessing crash you experienced earlier
    )

if __name__ == "__main__":
    main()
