import os
from ultralytics import YOLO
import torch

def train_model_v2():
    print("Starting Model V2 Training...")
    
    # 1. We upgrade to the YOLOv8 Medium model ("bigger brain")
    # This provides significantly more parameters for better accuracy
    model = YOLO("yolov8m.pt") 

    # 2. Train the model using the brand new V2 dataset
    # We use heavy augmentations to simulate murky underwater conditions
    results = model.train(
        data=r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2\drishti_v2.yaml",
        epochs=300,             # Push for maximum learning
        patience=50,            # Wait longer before early stopping (helps get out of local minima)
        batch=16,               # Standard batch size
        imgsz=640,              # Standard YOLO resolution
        device=0,               # Use GPU
        workers=0,              # REQUIRED FOR WINDOWS: Prevents the file I/O closed bug!
        project="E:/GITHUB/a sih 2026/models/v2",
        name="detector_v2",
        
        # --- Heavy Underwater Augmentations ---
        mosaic=1.0,             # Stitch 4 images together (great for small objects like mines)
        mixup=0.2,              # Blend images together
        hsv_s=0.5,              # Randomly shift saturation
        hsv_v=0.5,              # Randomly shift brightness (simulates deep water lighting)
        degrees=15.0,           # Random rotations (sonar can hit objects at angles)
        translate=0.1,          # Shift the image slightly
        scale=0.5               # Zoom in/out to handle different depths
    )
    
    print("\nTraining V2 complete! Model saved to E:/GITHUB/a sih 2026/models/v2/detector_v2")

if __name__ == '__main__':
    # Fix for multiprocessing on Windows just in case
    torch.multiprocessing.freeze_support()
    train_model_v2()
