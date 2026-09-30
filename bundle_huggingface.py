import os
import shutil

def main():
    base_dir = r"E:\GITHUB\a sih 2026"
    deploy_dir = os.path.join(base_dir, "huggingface_deployment")
    
    # 1. Create clean deploy directory
    if os.path.exists(deploy_dir):
        shutil.rmtree(deploy_dir)
    os.makedirs(deploy_dir)
    
    # 2. Copy the AI folder (ignoring pycache and reference)
    shutil.copytree(
        os.path.join(base_dir, "ai"), 
        os.path.join(deploy_dir, "ai"),
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'reference')
    )
    
    # 3. Copy the specific YOLO model
    model_dest_dir = os.path.join(deploy_dir, "models", "v6", "detector_v6_p2_sss", "weights")
    os.makedirs(model_dest_dir, exist_ok=True)
    shutil.copy2(
        os.path.join(base_dir, "models", "v6", "detector_v6_p2_sss", "weights", "best.pt"),
        os.path.join(model_dest_dir, "best.pt")
    )
    
    # 4. Create Dockerfile
    dockerfile_content = """FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for OpenCV
RUN apt-get update && apt-get install -y \\
    libgl1-mesa-glx \\
    libglib2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

# Copy all your backend code and models into the Docker container
COPY ai /app/ai
COPY models /app/models
COPY requirements.txt /app/requirements.txt

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Hugging Face Spaces exposes port 7860
EXPOSE 7860

# Ensure Python can find the ai module
ENV PYTHONPATH=/app

# Start the FastAPI server
CMD ["uvicorn", "ai.api.gate_f8_api_server:app", "--host", "0.0.0.0", "--port", "7860"]
"""
    with open(os.path.join(deploy_dir, "Dockerfile"), "w") as f:
        f.write(dockerfile_content)
        
    # 5. Create requirements.txt
    requirements = """fastapi
uvicorn
ultralytics
scikit-learn
opencv-python
pydantic
python-multipart
joblib
"""
    with open(os.path.join(deploy_dir, "requirements.txt"), "w") as f:
        f.write(requirements)
        
    print(f"Deployment folder successfully bundled at: {deploy_dir}")

if __name__ == "__main__":
    main()
