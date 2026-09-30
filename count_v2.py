import os
import glob

def get_counts(labels_dir):
    images = {'0':0, '1':0, '2':0, '3':0, '4':0}
    boxes = {'0':0, '1':0, '2':0, '3':0, '4':0}
    bg = 0
    files = glob.glob(os.path.join(labels_dir, "*.txt"))
    for f in files:
        with open(f, 'r') as file:
            lines = [l.strip().split()[0] for l in file.readlines() if l.strip()]
            if not lines:
                bg += 1
            else:
                for cls in set(lines):
                    if cls in images:
                        images[cls] += 1
                for cls in lines:
                    if cls in boxes:
                        boxes[cls] += 1
    return images, boxes, bg

train_img, train_box, train_bg = get_counts(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2\train\labels")
val_img, val_box, val_bg = get_counts(r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v2\val\labels")

print("--- DRISHTI V2 TRAIN SET ---")
print(f"crab_pot (0): {train_img['0']} images, {train_box['0']} boxes")
print(f"submarine_pipeline (1): {train_img['1']} images, {train_box['1']} boxes")
print(f"shipwreck (2): {train_img['2']} images, {train_box['2']} boxes")
print(f"ghost_net (3): {train_img['3']} images, {train_box['3']} boxes")
print(f"mine_cylinder (4): {train_img['4']} images, {train_box['4']} boxes")
print(f"background: {train_bg} images\n")

print("--- DRISHTI V2 VAL SET ---")
print(f"crab_pot (0): {val_img['0']} images, {val_box['0']} boxes")
print(f"submarine_pipeline (1): {val_img['1']} images, {val_box['1']} boxes")
print(f"shipwreck (2): {val_img['2']} images, {val_box['2']} boxes")
print(f"ghost_net (3): {val_img['3']} images, {val_box['3']} boxes")
print(f"mine_cylinder (4): {val_img['4']} images, {val_box['4']} boxes")
print(f"background: {val_bg} images")
