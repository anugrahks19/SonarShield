from ultralytics import YOLO
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python predict.py <path_to_image>")
        return
        
    image_path = sys.argv[1]
    
    # Load the best baseline model we have right now (the Drishti one)
    # Once V1 is trained, you change this path to: E:\GITHUB\a sih 2026\models\v1\detector_v1\weights\best.pt
    model_path = r"E:\GITHUB\a sih 2026\models\pretrained\drishti\best_detector.pt"
    model = YOLO(model_path)
    
    # Run prediction
    print(f"Running inference on {image_path}...")
    results = model(image_path)
    
    # Display results
    for r in results:
        print("\n--- Detection Results ---")
        if len(r.boxes) == 0:
            print("No objects detected.")
            continue
            
        for box in r.boxes:
            class_id = int(box.cls[0])
            conf = float(box.conf[0])
            coords = [round(c, 2) for c in box.xyxy[0].tolist()]
            
            # Use model class names if available, otherwise just ID
            class_name = model.names[class_id] if hasattr(model, 'names') else f"Class {class_id}"
            
            print(f"Detected: {class_name} | Confidence: {conf:.2f} | BBox: {coords}")
            
        # Optional: uncomment to visually pop open the image with bounding boxes
        # r.show()

if __name__ == "__main__":
    main()
