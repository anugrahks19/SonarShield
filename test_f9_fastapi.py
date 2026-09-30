import os
import sys
import time
import requests
import subprocess

def run_test():
    server_env = os.environ.copy()
    server_env["PYTHONPATH"] = r"E:\GITHUB\a sih 2026\ai"
    
    print("Starting FastAPI server...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.gate_f8_api_server:app", "--host", "127.0.0.1", "--port", "8000"],
        env=server_env,
        cwd=r"E:\GITHUB\a sih 2026\ai"
    )
    
    try:
        # Wait for server to start
        print("Waiting for server to start...")
        for _ in range(30):
            try:
                resp = requests.get("http://127.0.0.1:8000/health")
                if resp.status_code == 200:
                    print("Server is up and running!\n")
                    break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(2)
        else:
            print("Server failed to start in time.")
            return

        print("--- GET /health ---")
        resp = requests.get("http://127.0.0.1:8000/health")
        print(f"Status: {resp.status_code}")
        print(f"Components: {resp.json().get('components')}\n")
        
        print("--- POST /detect ---")
        img_path = r"E:\GITHUB\a sih 2026\datasets\drishti_sss_v3\val_clean\images\Contact_105_sslo_png_jpg.rf.4ef20d167e305a8cd5713496355c6f40.jpg"
        with open(img_path, "rb") as f:
            resp = requests.post("http://127.0.0.1:8000/detect", files={"file": ("Contact_105.jpg", f, "image/jpeg")}, data={"run_tiled_auxiliary": "true"})
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}\n")

        print("--- POST /analyze ---")
        with open(img_path, "rb") as f:
            resp = requests.post("http://127.0.0.1:8000/analyze", files={"file": ("Contact_105.jpg", f, "image/jpeg")}, data={"run_tiled_auxiliary": "true", "return_visual_audit": "false"})
        print(f"Status: {resp.status_code}")
        analysis_id = resp.json().get('analysis_id')
        print(f"Analysis ID: {analysis_id}")
        print(f"Candidate Count: {resp.json().get('summary', {}).get('candidate_count')}\n")

        print("--- POST /report (Valid) ---")
        resp = requests.post("http://127.0.0.1:8000/report", json={"analysis_ids": [analysis_id], "format": "JSON"})
        print(f"Status: {resp.status_code}")
        print(f"Report URL: {resp.json().get('report_url')}\n")

        print("--- POST /report (Invalid) ---")
        resp = requests.post("http://127.0.0.1:8000/report", json={"analysis_ids": ["INVALID"], "format": "JSON"})
        print(f"Status: {resp.status_code}")
        print(f"Error: {resp.json()}\n")
        
    finally:
        print("Shutting down server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    run_test()
