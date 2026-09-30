import os
import sys
import json
import hashlib
from importlib import metadata

def sha256_file(filepath):
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def main():
    freeze_dir = r"E:\GITHUB\a sih 2026\backend_freeze"
    hashes_dir = os.path.join(freeze_dir, "hashes")
    os.makedirs(hashes_dir, exist_ok=True)
    
    # 1. Hashing
    detector_path = r"E:\GITHUB\a sih 2026\models\v6\detector_v6_p2_sss\weights\best.pt"
    fusion_path = r"E:\GITHUB\a sih 2026\ai\fusion\weights\gate_d_fusion_model.pkl"
    policy_path = r"E:\GITHUB\a sih 2026\ai\reliability\weights\score_policy.json"
    calib_path = r"E:\GITHUB\a sih 2026\ai\reliability\weights\f4_f5_calibration.json"
    
    with open(os.path.join(hashes_dir, "detector.sha256"), "w") as f:
        f.write(sha256_file(detector_path))
        
    with open(os.path.join(hashes_dir, "fusion.sha256"), "w") as f:
        f.write(sha256_file(fusion_path))
        
    with open(os.path.join(hashes_dir, "decision_policy.sha256"), "w") as f:
        f.write(sha256_file(policy_path))
        
    with open(os.path.join(hashes_dir, "calibration.sha256"), "w") as f:
        f.write(sha256_file(calib_path))
        
    # 2. Environment
    env_info = {}
    packages = ["torch", "ultralytics", "numpy", "scikit-learn", "fastapi", "pydantic", "opencv-python", "onnxruntime"]
    
    for pkg in packages:
        try:
            env_info[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            env_info[pkg] = "NOT_FOUND"
            
    env_info["python"] = sys.version
    env_info["platform"] = sys.platform
    
    with open(os.path.join(freeze_dir, "environment.json"), "w") as f:
        json.dump(env_info, f, indent=2)
        
    print("Hashes and environment successfully recorded.")

if __name__ == "__main__":
    main()
