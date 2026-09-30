from pathlib import Path
import cv2
import random
import csv
import math
import numpy as np

# ============================================================
# CONFIG
# ============================================================

IMAGE_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2\train\images")
LABEL_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2\train\labels")
OUT_DIR = Path(r"E:\GITHUB\a sih 2026\datasets\ai4shipwreck_bbox_audit")

SAMPLE_COUNT = 30
SEED = 42

OUT_DIR.mkdir(parents=True, exist_ok=True)
random.seed(SEED)

# ============================================================
# FIND IMAGE/LABEL PAIRS
# ============================================================

image_exts = {".jpg", ".jpeg", ".png", ".bmp"}

images = [
    p for p in IMAGE_DIR.rglob("*")
    if p.suffix.lower() in image_exts and p.name.startswith("ai4_")
]

pairs = []

for img_path in images:
    label_path = LABEL_DIR / f"{img_path.stem}.txt"
    if label_path.exists():
        pairs.append((img_path, label_path))

print(f"Found {len(pairs)} image/label pairs (AI4Shipwrecks Training Set)")

if not pairs:
    raise RuntimeError("No matching image/label pairs found.")

# ============================================================
# READ YOLO BOX
# ============================================================

records = []

for img_path, label_path in pairs:
    image = cv2.imread(str(img_path))
    if image is None:
        continue

    h, w = image.shape[:2]

    with open(label_path, "r") as f:
        lines = [x.strip() for x in f if x.strip()]

    for line in lines:
        parts = line.split()
        if len(parts) != 5:
            continue

        cls, xc, yc, bw, bh = map(float, parts)
        if int(cls) != 2:
            continue

        x1 = max(0, int((xc - bw / 2) * w))
        y1 = max(0, int((yc - bh / 2) * h))
        x2 = min(w - 1, int((xc + bw / 2) * w))
        y2 = min(h - 1, int((yc + bh / 2) * h))

        box_w = x2 - x1
        box_h = y2 - y1

        bbox_area = box_w * box_h
        image_area = w * h
        bbox_area_ratio = bbox_area / image_area if image_area > 0 else 0

        records.append({
            "image": img_path,
            "label": label_path,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "width_ratio": box_w / w,
            "height_ratio": box_h / h,
            "bbox_area_ratio": bbox_area_ratio,
            "aspect_ratio": box_w / max(box_h, 1),
        })

print(f"Found {len(records)} shipwreck boxes")
if not records:
    raise RuntimeError("No class-2 shipwreck boxes found.")

# ============================================================
# SELECT SAMPLES
# ============================================================

random_records = random.sample(records, min(20, len(records)))
largest_records = sorted(records, key=lambda x: x["bbox_area_ratio"], reverse=True)[:5]
wide_records = sorted(records, key=lambda x: x["aspect_ratio"], reverse=True)[:5]

selected = []
seen = set()

for r in random_records + largest_records + wide_records:
    key = (str(r["image"]), r["x1"], r["y1"], r["x2"], r["y2"])
    if key not in seen:
        selected.append(r)
        seen.add(key)

selected = selected[:SAMPLE_COUNT]

# ============================================================
# DRAW IMAGES
# ============================================================

thumbs = []
for i, r in enumerate(selected):
    image = cv2.imread(str(r["image"]))
    if image is None:
        continue

    x1, y1, x2, y2 = (r["x1"], r["y1"], r["x2"], r["y2"])
    
    cv2.rectangle(image, (x1, y1), (x2, y2), (255, 255, 255), 3)

    text = f"area={r['bbox_area_ratio']:.2f} AR={r['aspect_ratio']:.2f}"
    cv2.putText(image, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    out_path = OUT_DIR / f"sample_{i+1:02d}.jpg"
    cv2.imwrite(str(out_path), image)

    thumb = cv2.resize(image, (320, 240))
    thumbs.append(thumb)

# ============================================================
# CONTACT SHEET
# ============================================================

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

csv_path = OUT_DIR / "bbox_audit.csv"
with open(csv_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["image", "bbox_area_ratio", "width_ratio", "height_ratio", "aspect_ratio"])
    for r in selected:
        writer.writerow([
            r["image"].name,
            f"{r['bbox_area_ratio']:.4f}",
            f"{r['width_ratio']:.4f}",
            f"{r['height_ratio']:.4f}",
            f"{r['aspect_ratio']:.4f}",
        ])

print("\nAUDIT COMPLETE")
print(f"Contact sheet: {OUT_DIR / 'contact_sheet.png'}")
print(f"CSV: {csv_path}")
