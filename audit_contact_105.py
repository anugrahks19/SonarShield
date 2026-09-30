import cv2
from pathlib import Path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "ai"))
from detection.tiled_detector import TiledDetector

def main():
    model_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
    img_path = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\images\Contact_105_sslo_png_jpg.rf.4ef20d167e305a8cd5713496355c6f40.jpg"
    
    detector = TiledDetector(model_path, conf=0.15, iou=0.7)
    image = cv2.imread(img_path)
    
    global_preds = detector.predict(image, trigger_conf=-1.0, pure_tiled=False)
    tiled_preds = detector.predict(image, trigger_conf=2.0, pure_tiled=True)
    
    print("GLOBAL predictions:")
    for p in global_preds:
        print(p)
        
    print("\nTILED predictions:")
    for p in tiled_preds:
        print(p)

    def compute_iou(boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
        boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
        boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
        
        return interArea / float(boxAArea + boxBArea - interArea)

    for i, gp in enumerate(global_preds):
        for j, tp in enumerate(tiled_preds):
            gx1, gy1, gx2, gy2 = gp['bbox']
            tx1, ty1, tx2, ty2 = tp['bbox']
            gcx = (gx1 + gx2) / 2
            gcy = (gy1 + gy2) / 2
            tcx = (tx1 + tx2) / 2
            tcy = (ty1 + ty2) / 2
            dist = ((tcx - gcx)**2 + (tcy - gcy)**2)**0.5
            iou = compute_iou(gp['bbox'], tp['bbox'])
            print(f"\nGLOBAL {i} vs TILED {j}:")
            print(f"Center Distance: {dist:.2f} px")
            print(f"IoU: {iou:.3f}")

if __name__ == "__main__":
    main()
