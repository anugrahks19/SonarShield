import os
import cv2
import json
import matplotlib.pyplot as plt
import numpy as np

def draw_audit_panel(image_path, evidence_data, out_path):
    img = cv2.imread(image_path)
    if img is None:
        return
        
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    bbox = evidence_data['bbox']
    x1, y1, x2, y2 = map(int, bbox)
    
    # 1. Original SSS (Crop around the detection for context)
    pad = 100
    h, w = img.shape[:2]
    cx1 = max(0, x1 - pad)
    cy1 = max(0, y1 - pad)
    cx2 = min(w, x2 + pad)
    cy2 = min(h, y2 + pad)
    
    orig_crop = img_rgb[cy1:cy2, cx1:cx2].copy()
    
    # 2. Detection + bounding box
    bbox_img = img_rgb.copy()
    color = (255, 0, 0) if evidence_data['source'] == 'GLOBAL' else (0, 0, 255)
    cv2.rectangle(bbox_img, (x1, y1), (x2, y2), color, 2)
    bbox_crop = bbox_img[cy1:cy2, cx1:cx2].copy()
    
    # 3. Local seabed region (ring)
    seabed_img = img_rgb.copy()
    # Draw ring boundaries
    cv2.rectangle(seabed_img, (max(0, x1-20), max(0, y1-20)), (min(w, x2+20), min(h, y2+20)), (0, 255, 0), 1)
    cv2.rectangle(seabed_img, (x1, y1), (x2, y2), (255, 0, 0), 1)
    seabed_crop = seabed_img[cy1:cy2, cx1:cx2].copy()
    
    # 4. Shadow candidate
    shadow_img = img_rgb.copy()
    shadow_bbox = evidence_data['shadow']['shadow_bbox']
    if shadow_bbox:
        sx1, sy1, sx2, sy2 = map(int, shadow_bbox)
        cv2.rectangle(shadow_img, (sx1, sy1), (sx2, sy2), (255, 255, 0), 2)
    shadow_crop = shadow_img[cy1:cy2, cx1:cx2].copy()
    
    # Plotting
    fig, axes = plt.subplots(1, 5, figsize=(20, 4))
    
    axes[0].imshow(orig_crop)
    axes[0].set_title("Original SSS Context")
    axes[0].axis('off')
    
    axes[1].imshow(bbox_crop)
    axes[1].set_title(f"Detection ({evidence_data['source']})")
    axes[1].axis('off')
    
    axes[2].imshow(seabed_crop)
    axes[2].set_title("Local Seabed Ring")
    axes[2].axis('off')
    
    axes[3].imshow(shadow_crop)
    axes[3].set_title("Shadow Candidate")
    axes[3].axis('off')
    
    # 5. Evidence values text
    axes[4].axis('off')
    flags = [k for k, v in evidence_data['quality']['artifact_flags'].items() if v]
    text = (
        f"Class: {evidence_data['class']}\n"
        f"Source: {evidence_data['source']}\n"
        f"AI Conf: {evidence_data['confidence']:.3f}\n"
        f"Local Contrast: {evidence_data['seabed']['local_contrast']:.3f}\n"
        f"Shadow Score: {evidence_data['shadow']['shadow_candidate_presence']:.3f}\n"
        f"Shadow Ratio: {evidence_data['shadow']['area_ratio']:.3f}\n"
        f"Boundary Str: {evidence_data['quality']['boundary_strength']:.3f}\n"
        f"Artifacts: {', '.join(flags) if flags else 'None'}"
    )
    axes[4].text(0.1, 0.5, text, fontsize=12, va='center', ha='left', family='monospace')
    
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()

def run_audit():
    results_path = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_results.json"
    out_dir = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_audit"
    os.makedirs(out_dir, exist_ok=True)
    
    with open(results_path, 'r') as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} candidates.")
    
    # Shuffle and pick top 30 to audit
    import random
    random.seed(42)
    sample = random.sample(data, min(30, len(data)))
    
    for i, item in enumerate(sample):
        out_path = os.path.join(out_dir, f"audit_{i:02d}_{item['evidence']['source']}_{item['evidence']['class']}.jpg")
        draw_audit_panel(item['image_path'], item['evidence'], out_path)
        
    print(f"Generated {len(sample)} visual audit panels in {out_dir}")

if __name__ == "__main__":
    run_audit()
