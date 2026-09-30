import os
import json
import glob
from collections import defaultdict
from pathlib import Path

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def scan_datasets():
    datasets_dir = r"E:\GITHUB\a sih 2026\datasets"
    
    # Target folders that might contain raw data
    targets = [
        "AI4Shipwrecks",
        "MILCONOMBO Side-Scan Sonar Mine Dataset",
        "drishti_sss"
    ]
    
    report = defaultdict(lambda: {
        "image_formats": set(),
        "annotation_formats": set(),
        "metadata_files": [],
        "metadata_fields_found": set(),
        "geotiff_tags_found": set(),
        "exif_tags_found": set()
    })
    
    for t in targets:
        full_path = os.path.join(datasets_dir, t)
        if not os.path.exists(full_path):
            continue
            
        print(f"Scanning {t}...")
        
        for root, dirs, files in os.walk(full_path):
            for file in files:
                ext = Path(file).suffix.lower()
                
                if ext in ['.jpg', '.png', '.jpeg', '.tif', '.tiff', '.bmp']:
                    report[t]["image_formats"].add(ext)
                    # Check first few images for EXIF/TIFF tags
                    if len(report[t]["image_formats"]) <= 20 and HAS_PIL and ext in ['.tif', '.tiff', '.jpg', '.jpeg']:
                        try:
                            img = Image.open(os.path.join(root, file))
                            if hasattr(img, 'tag_v2'):
                                for tag, value in img.tag_v2.items():
                                    report[t]["geotiff_tags_found"].add(tag)
                            if hasattr(img, '_getexif') and img._getexif():
                                for tag, value in img._getexif().items():
                                    decoded = TAGS.get(tag, tag)
                                    report[t]["exif_tags_found"].add(str(decoded))
                        except Exception as e:
                            pass
                elif ext in ['.txt', '.xml', '.json', '.csv']:
                    # Heuristic for annotations vs metadata
                    if "train" in root.lower() or "val" in root.lower() or "test" in root.lower():
                        if ext == '.txt':
                            report[t]["annotation_formats"].add("YOLO (.txt)")
                        elif ext == '.xml':
                            report[t]["annotation_formats"].add("VOC (.xml)")
                        elif ext == '.json':
                            report[t]["annotation_formats"].add("COCO (.json)")
                            
                    if ext in ['.json', '.csv', '.xml']:
                        report[t]["metadata_files"].append(os.path.join(root, file))
                        
                        # Inspect JSON for potential geo keys
                        if ext == '.json' and len(report[t]["metadata_fields_found"]) < 50:
                            try:
                                with open(os.path.join(root, file), 'r') as f:
                                    j = json.load(f)
                                    if isinstance(j, dict):
                                        for k in j.keys():
                                            report[t]["metadata_fields_found"].add(k)
                                            if isinstance(j[k], dict):
                                                for k2 in j[k].keys():
                                                    report[t]["metadata_fields_found"].add(k2)
                                    elif isinstance(j, list) and len(j) > 0 and isinstance(j[0], dict):
                                        for k in j[0].keys():
                                            report[t]["metadata_fields_found"].add(k)
                            except:
                                pass
                                
    print("\n\n--- GATE F1: DISCOVERY REPORT ---")
    for t, d in report.items():
        print(f"\nDataset: {t}")
        print(f"Image Formats: {list(d['image_formats'])}")
        print(f"Annotation Formats: {list(d['annotation_formats'])}")
        print(f"Sample Metadata Files: {d['metadata_files'][:5]}")
        
        geo_keywords = ['lat', 'lon', 'gps', 'pos', 'head', 'range', 'swath', 'depth', 'alt', 'sensor', 'utm', 'epsg']
        
        geo_found = [k for k in d['metadata_fields_found'] if any(g in str(k).lower() for g in geo_keywords)]
        if geo_found:
            print(f"Potential Geo/Navigation Metadata Fields (JSON/CSV): {geo_found}")
            
        if d['geotiff_tags_found']:
            # List standard GeoTIFF tag IDs if present (e.g. 34735, 34736, 34737)
            geo_tags = [t for t in d['geotiff_tags_found'] if t in [33550, 33922, 34735, 34736, 34737]]
            print(f"GeoTIFF Tags Found: {geo_tags}")
            print(f"All TIFF Tags: {list(d['geotiff_tags_found'])[:20]}")
            
        if d['exif_tags_found']:
            print(f"EXIF Tags Found: {list(d['exif_tags_found'])[:10]}")
            
        print("-" * 50)

if __name__ == "__main__":
    scan_datasets()
