import torch
from ultralytics import YOLO

def train_model_v2_hn():
    print("Starting V2-HN: PURE DATASET ABLATION STUDY")
    
    # EXACT V1 CHECKPOINT
    v1_best_weights = r"E:\GITHUB\a sih 2026\models\v1\detector_v1-2\weights\best.pt"
    model = YOLO(v1_best_weights) 
    
    # Train using the exact same hyperparameters as V1 (from args.yaml)
    # The ONLY variable changing is the dataset.
    model.train(
        data=r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2\drishti_v2.yaml",
        
        # Match V1 Training Config
        epochs=50,
        patience=10,
        imgsz=640,
        device=0,
        batch=16,
        workers=0,
        
        # Directories
        project=r"E:\GITHUB\a sih 2026\models\v2",
        name="detector_v2_hn",
        
        # We explicitly rely on the Ultralytics defaults to match V1.
        # DO NOT override hsv_h, degrees, mosaic, etc., because V1
        # used the standard defaults recorded in its args.yaml.
    )
    
if __name__ == "__main__":
    torch.multiprocessing.freeze_support()
    train_model_v2_hn()
