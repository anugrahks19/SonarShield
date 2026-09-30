from ultralytics import YOLO

def train_model_v5():
    # V5 = clean YOLOv8m baseline
    model = YOLO("yolov8m.pt")

    model.train(
        data=r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\drishti_v3.yaml",
        epochs=50,
        patience=10,
        imgsz=640,
        batch=4,
        device=0,
        workers=0,
        project=r"E:\GITHUB\a sih 2026\models\v5",
        name="detector_v5_m640",
    )

if __name__ == "__main__":
    train_model_v5()
