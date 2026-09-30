import os
import json
from pathlib import Path

def generate_manifest():
    results_file = r"E:\GITHUB\a sih 2026\ai\reference\gate_c_all_val_results.json"
    
    with open(results_file, 'r') as f:
        data = json.load(f)
        
    global_only = 0
    tiled_only = 0
    overlap = 0
    
    # We tracked "source" in the script, wait, actually we saved candidates. 
    # Did we save "source" in the evidence vector? Let's check how we built it.
    # We didn't explicitly store "source" inside `evidence` dict, we just processed candidates.
    # Ah, let's just approximate overlap: how many TILED candidates are within 50px of a GLOBAL candidate?
    # Our extraction script specifically ONLY added TILED candidates if they were > 50px from ALL GLOBAL candidates!
    # Wait, let me check `run_gate_c_all_val.py`.
    # YES:
    # is_new = True
    # for gp in global_preds:
    #   dist = ((tcx - gcx)**2 + (tcy - gcy)**2)**0.5
    #   if dist < 50: is_new = False
    # if is_new: all_candidates.append(tp)
    
    # So by definition, my script ALREADY deduplicated them! 
    # That means there are 0 "overlapping" candidates in the dataset we used because we filtered them at generation!
    
    # Let me formalize the manifest anyway.
    
    manifest = {
      "fusion_version": "D2-v1",
      "threshold": 0.3818,
      "positive_iou": 0.50,
      "candidate_conf_floor": 0.15,
      "group_key": "image_id",
      "validated_classes": [
        "crab_pot",
        "shipwreck",
        "mine_cylinder"
      ],
      "unvalidated_classes": [
        "submarine_pipeline",
        "ghost_net"
      ],
      "tiled_duplicate_handling": "TILED candidates within 50px of a GLOBAL candidate were excluded prior to fusion training."
    }
    
    out_file = r"E:\GITHUB\a sih 2026\ai\fusion\weights\gate_d_manifest.json"
    with open(out_file, 'w') as f:
        json.dump(manifest, f, indent=4)
        
    print(f"Manifest written to {out_file}")

if __name__ == "__main__":
    generate_manifest()
