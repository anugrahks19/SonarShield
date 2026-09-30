import os
import cv2
import matplotlib.pyplot as plt
import numpy as np
from preprocessing.pipeline import preprocess_sonar_image
import random

def create_contact_sheet():
    val_clean_img_dir = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\images"
    all_images = os.listdir(val_clean_img_dir)
    
    # We ideally pick known crabs, wrecks, mines, etc. For this script, we'll sample 15 randomly for a clean plot
    sample_images = random.sample(all_images, 10)
    
    modes = {
        "SOURCE": {"normalize": False, "denoise_method": "none", "use_clahe": False},
        "NORM": {"normalize": True, "denoise_method": "none", "use_clahe": False},
        "NORM_DENOISE": {"normalize": True, "denoise_method": "bilateral", "use_clahe": False},
        "NORM_CLAHE": {"normalize": True, "denoise_method": "none", "use_clahe": True},
        "ALL": {"normalize": True, "denoise_method": "bilateral", "use_clahe": True}
    }
    
    fig, axes = plt.subplots(len(sample_images), len(modes), figsize=(20, 4 * len(sample_images)))
    
    for i, img_file in enumerate(sample_images):
        img_path = os.path.join(val_clean_img_dir, img_file)
        for j, (mode_name, settings) in enumerate(modes.items()):
            processed = preprocess_sonar_image(img_path, **settings)
            ax = axes[i, j]
            if len(processed.shape) == 3:
                processed = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
            ax.imshow(processed, cmap='gray')
            if i == 0:
                ax.set_title(mode_name, fontsize=14, fontweight='bold')
            ax.axis('off')
            
    plt.tight_layout()
    plt.savefig(r"E:\GITHUB\a sih 2026\preprocessing_contact_sheet.jpg", bbox_inches='tight', dpi=150)
    print("Saved preprocessing_contact_sheet.jpg")

if __name__ == "__main__":
    create_contact_sheet()
