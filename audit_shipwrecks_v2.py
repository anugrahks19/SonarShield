from pathlib import Path
import cv2
import random
import csv
import math
import numpy as np

# ============================================================
# CONFIG
# ============================================================

# Pointing to the ORIGINAL AI4Shipwrecks dataset to use the actual masks
AI4_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\AI4Shipwrecks\AI4Shipwrecks\train")
IMAGE_DIR = AI4_DIR / "images"
MASK_DIR = AI4_DIR / "labels" # The masks are actually PNGs stored in the labels folder
OUT_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\ai4shipwreck_bbox_audit_v2")

SAMPLE_COUNT = 30
SEED = 42

OUT_DIR.mkdir(parents=True, exist_ok=True)
random.seed(SEED)

# ============================================================
# READ MASKS AND CALCULATE RATIOS
# ============================================================

records = []
masks = list(MASK_DIR.glob("*.png"))

for mask_path in masks:
    # Attempt to load the corresponding image
    img_path = IMAGE_DIR / mask_path.name
    if not img_path.exists():
        continue
        
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        continue
        
    h, w = mask.shape
    points = cv2.findNonZero(mask)
    if points is None:
        continue # Empty mask
        
    # mask area = number of white pixels
    mask_area = cv2.countNonZero(mask)
    
    # Calculate bounding box
    x, y, bw, bh = cv2.boundingRect(points)
    bbox_area = bw * bh
    
    if bbox_area == 0:
        continue
        
    mask_fill_ratio = mask_area / bbox_area
    bbox_area_ratio = bbox_area / (w * h)
    aspect_ratio = bw / max(bh, 1)
    
    records.append({
        "image": img_path,
        "mask": mask_path,
        "x1": x,
        "y1": y,
        "x2": x + bw,
        "y2": y + bh,
        "bbox_area": bbox_area,
        "mask_area": mask_area,
        "bbox_area_ratio": bbox_area_ratio,
        "mask_fill_ratio": mask_fill_ratio,
        "aspect_ratio": aspect_ratio,
    })

print(f"Found {len(records)} valid Shipwreck masks in train split.")

# ============================================================
# COMPUTE STATISTICS
# ============================================================

mask_fills = [r["mask_fill_ratio"] for r in records]
bbox_ratios = [r["bbox_area_ratio"] for r in records]

print("\n--- MASK FILL RATIO STATS ---")
print(f"Min:    {np.min(mask_fills):.4f}")
print(f"25th:   {np.percentile(mask_fills, 25):.4f}")
print(f"Median: {np.median(mask_fills):.4f}")
print(f"75th:   {np.percentile(mask_fills, 75):.4f}")
print(f"90th:   {np.percentile(mask_fills, 90):.4f}")
print(f"Max:    {np.max(mask_fills):.4f}")

print("\n--- BBOX AREA RATIO STATS ---")
print(f"Min:    {np.min(bbox_ratios):.4f}")
print(f"25th:   {np.percentile(bbox_ratios, 25):.4f}")
print(f"Median: {np.median(bbox_ratios):.4f}")
print(f"75th:   {np.percentile(bbox_ratios, 75):.4f}")
print(f"90th:   {np.percentile(bbox_ratios, 90):.4f}")
print(f"Max:    {np.max(bbox_ratios):.4f}")

# ============================================================
# SELECT SAMPLES
# ============================================================

random_records = random.sample(records, min(10, len(records)))
largest_bboxes = sorted(records, key=lambda x: x["bbox_area_ratio"], reverse=True)[:10]
lowest_fills = sorted(records, key=lambda x: x["mask_fill_ratio"], reverse=False)[:10]

selected = []
seen = set()

for r in random_records + largest_bboxes + lowest_fills:
    key = str(r["image"])
    if key not in seen:
        selected.append(r)
        seen.add(key)

selected = selected[:SAMPLE_COUNT]

# ============================================================
# DRAW IMAGES & CONTACT SHEET
# ============================================================

thumbs = []
for i, r in enumerate(selected):
    image = cv2.imread(str(r["image"]))
    mask = cv2.imread(str(r["mask"]), cv2.IMREAD_GRAYSCALE)
    if image is None or mask is None:
        continue

    # Create a red overlay for the mask
    overlay = np.zeros_like(image)
    overlay[mask > 0] = [0, 0, 255] # Red mask
    
    # Blend image and mask
    cv2.addWeighted(overlay, 0.5, image, 0.5, 0, image)

    x1, y1, x2, y2 = (r["x1"], r["y1"], r["x2"], r["y2"])
    
    # Draw Bounding Box (White)
    cv2.rectangle(image, (x1, y1), (x2, y2), (255, 255, 255), 3)

    # Text
    text1 = f"Fill: {r['mask_fill_ratio']:.2f}"
    text2 = f"BoxArea: {r['bbox_area_ratio']:.2f}"
    cv2.putText(image, text1, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.putText(image, text2, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2, cv2.LINE_AA)

    out_path = OUT_DIR / f"sample_{i+1:02d}.jpg"
    cv2.imwrite(str(out_path), image)

    thumb = cv2.resize(image, (320, 240))
    thumbs.append(thumb)

cols = 5
rows = math.ceil(len(thumbs) / cols)

sheet_rows = []
for r in range(rows):
    row_thumbs = thumbs[r * cols:(r + 1) * cols]
    if len(row_thumbs) < cols:
        row_thumbs += [np.ones((240, 320, 3), dtype="uint8") * 255] * (cols - len(row_thumbs))
    sheet_rows.append(cv2.hconcat(row_thumbs))

if sheet_rows:
    sheet = cv2.vconcat(sheet_rows)
    cv2.imwrite(str(OUT_DIR / "contact_sheet.png"), sheet)

# ============================================================
# CSV
# ============================================================

csv_path = OUT_DIR / "mask_audit.csv"
with open(csv_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["image", "bbox_area_ratio", "mask_fill_ratio", "aspect_ratio"])
    for r in records:
        writer.writerow([
            r["image"].name,
            f"{r['bbox_area_ratio']:.4f}",
            f"{r['mask_fill_ratio']:.4f}",
            f"{r['aspect_ratio']:.4f}",
        ])

print("\nAUDIT COMPLETE")
print(f"Contact sheet: {OUT_DIR / 'contact_sheet.png'}")
print(f"CSV: {csv_path}")
