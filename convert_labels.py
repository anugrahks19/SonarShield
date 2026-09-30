import os
import json
from PIL import Image

src_base = r"E:\GITHUB\a sih 2026\datasets\crab_pot"
dst_base = r"E:\GITHUB\a sih 2026\datasets\drishti_sss"
splits = {"train": "train", "valid": "val", "test": "test"}

total_labels = 0
for src_split, dst_split in splits.items():
    src_dir = os.path.join(src_base, src_split)
    jsonl_path = os.path.join(src_dir, "metadata.jsonl")
    if not os.path.exists(jsonl_path): continue

    dst_lbl_dir = os.path.join(dst_base, dst_split, "labels")
    os.makedirs(dst_lbl_dir, exist_ok=True)
    
    with open(jsonl_path, 'r') as f:
        lines = f.readlines()
        
    for line in lines:
        data = json.loads(line.strip())
        img_name = data['file_name']
        img_path = os.path.join(src_dir, img_name)
        
        if not os.path.exists(img_path): continue
            
        with Image.open(img_path) as img:
            img_w, img_h = img.size
            
        txt_name = os.path.splitext(img_name)[0] + ".txt"
        txt_path = os.path.join(dst_lbl_dir, txt_name)
        
        yolo_lines = []
        if 'objects' in data and 'bbox' in data['objects']:
            for bbox in data['objects']['bbox']:
                x, y, w, h = bbox
                x_c, y_c = x + w/2, y + h/2
                yolo_lines.append(f"0 {x_c/img_w:.6f} {y_c/img_h:.6f} {w/img_w:.6f} {h/img_h:.6f}")
                
        with open(txt_path, 'w') as out_f:
            out_f.write("\n".join(yolo_lines) + "\n")
        total_labels += 1
        
print(f"Successfully generated {total_labels} YOLO labels!")
