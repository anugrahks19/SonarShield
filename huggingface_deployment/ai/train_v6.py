from ultralytics import YOLO

def train_v6():
    # Official YOLOv8 P2 architecture 
    # P2/4 head is intended for extra-small objects.
    print("Starting V6: YOLOv8s-P2 Architecture + SSS-Specific Augmentations")
    model = YOLO("yolov8s-p2.yaml").load("yolov8s.pt")

    model.train(
        data=r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\drishti_v3.yaml",
        epochs=80,
        patience=15,
        imgsz=640,
        batch=8,
        device=0,
        workers=0,
        project=r"E:\GITHUB\a sih 2026\models\v6",
        name="detector_v6_p2_sss",
        
        # SSS-oriented augmentation
        hsv_h=0.0,
        hsv_s=0.0,
        hsv_v=0.0,
        degrees=5.0,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=0.8,
        mixup=0.1,
        auto_augment=None,
        erasing=0.0,
        close_mosaic=10,
        seed=0,
        deterministic=True,
        amp=True,
    )

if __name__ == "__main__":
    train_v6()
