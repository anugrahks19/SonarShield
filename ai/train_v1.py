from ultralytics import YOLO
import os

def main():
    # 1. Path to the pre-trained Drishti model we downloaded
    # This acts as our foundational baseline
    pretrained_model_path = r"E:\GITHUB\a sih 2026\models\pretrained\drishti\best_detector.pt"
    
    # Verify the model exists
    if not os.path.exists(pretrained_model_path):
        raise FileNotFoundError(f"Could not find model at {pretrained_model_path}")
        
    print(f"Loading base model: {pretrained_model_path}")
    model = YOLO(pretrained_model_path)
    
    # 2. Path to your dataset configuration
    dataset_config = r"E:\GITHUB\a sih 2026\datasets\drishti_sss\drishti.yaml"
    
    if not os.path.exists(dataset_config):
        print(f"Warning: {dataset_config} not found. You must create your dataset splits first!")
        print("Run complete. Ready for data.")
        return

    # 3. Start Fine-Tuning (Model V1)
    # We fine-tune the baseline on the combined dataset (Ghost Pot + SubPipe)
    print("Starting Model V1 Training...")
    results = model.train(
        data=dataset_config,
        epochs=50,             # Epochs to run
        imgsz=640,             # Sonar image resolution
        batch=16,              # Batch size
        project=r"E:\GITHUB\a sih 2026\models\v1", # Save location
        name="detector_v1",    # Run name
        patience=10,           # Early stopping if no improvement
        device="0",            # Use GPU 0 (change to 'cpu' if no GPU)
        workers=0              # Fixes Windows "I/O operation on closed file" error
    )
    
    print(r"Training complete! Model saved to E:\GITHUB\a sih 2026\models\v1\detector_v1")

if __name__ == "__main__":
    main()
