# SONAR-SHIELD deployment guide — historical Docker/FastAPI proposal

> **Archived plan:** This file describes an earlier Docker/FastAPI Space proposal and its `VITE_API_URL` setting. The current public app uses a **Gradio** Space, `/analyze_image_gradio`, and `VITE_GRADIO_SPACE_ID`. Follow the [repository README](README.md) and [current integration guide](frontend/docs/HUGGING_FACE_INTEGRATION.md) for setup and deployment. The commands below are retained only as project history.

This was the original hosting proposal for the SONAR-SHIELD project.
- **Frontend**: Vercel (Fast, global CDN, perfect for React).
- **Backend API**: Hugging Face Spaces (Free 16GB RAM, natively supports large `.pt` and `.pkl` AI weights via Git LFS, Docker support).

---

## 1. What Goes Where? (The Repository Split)

You will maintain two separate upstream destinations for your code. 

### A. Push to GitHub (For Vercel)
GitHub strictly enforces a 100MB file limit. You will push your code here so Vercel can build your frontend.

**What to Push to GitHub:**
- `frontend/` (All React/Vite source code)
- `backend_freeze/` (Documentation and hashes)
- `deployment_guide.md`

**Add this to your `.gitignore` before pushing to GitHub:**
```text
# Ignore heavy ML weights and datasets for GitHub
datasets/
models/
**/*.pt
**/*.pkl
**/*.onnx

# Python/Node ignores
__pycache__/
.venv/
node_modules/
.env
```

### B. Push to Hugging Face (For Backend API)
Hugging Face Spaces acts as its own Git repository. Because it supports **Git LFS** (Large File Storage), you *can* and *should* push your heavy AI weights here.

**What to push to Hugging Face Space:**
- `ai/` folder (Your FastAPI server and inference logic)
- `models/v6/detector_v6_p2_sss/weights/best.pt` (Your frozen YOLO weights)
- `ai/fusion/weights/gate_d_fusion_model.pkl` (Your frozen Fusion weights)
- `Dockerfile` (Required by Hugging Face to run your API)
- `requirements.txt`

---

## 2. Deploying the Backend on Hugging Face Spaces

1. Create a free account on [Hugging Face](https://huggingface.co/).
2. Click **Create new Space**.
   - **Name**: `sonar-shield-api`
   - **License**: MIT (or your choice)
   - **Space SDK**: Select **Docker** (Blank).
   - **Space Hardware**: Free Tier (2 vCPU, 16GB RAM).
3. Clone the new Hugging Face repository to your local machine.
4. Copy your `ai/` folder and your frozen weight files into this cloned folder.
5. Create a `Dockerfile` at the root of the Hugging Face repo:

```dockerfile
# Dockerfile for Hugging Face Spaces
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy all your backend code and models into the Docker container
COPY ai /app/ai
COPY models /app/models

# Install Python packages
RUN pip install --no-cache-dir fastapi uvicorn ultralytics scikit-learn opencv-python pydantic python-multipart joblib

# Hugging Face Spaces exposes port 7860
EXPOSE 7860

# Ensure Python can find the ai module
ENV PYTHONPATH=/app

# Start the FastAPI server
CMD ["uvicorn", "ai.api.gate_f8_api_server:app", "--host", "0.0.0.0", "--port", "7860"]
```

6. Commit and push back to Hugging Face. The Space will automatically build the Docker container and start your API!
   - Your API URL will look like: `https://<your-username>-sonar-shield-api.hf.space`

---

## 3. Deploying the Frontend on Vercel

1. Inside your `frontend/` code, ensure you are not hardcoding `http://127.0.0.1:8000`. Instead, point your API calls to an environment variable:
   ```typescript
   const API_URL = import.meta.env.VITE_API_URL;
   fetch(`${API_URL}/analyze`, { ... })
   ```
2. Commit your code and push it to your **GitHub** repository.
3. Log into [Vercel](https://vercel.com/) and click **Add New Project**.
4. Import your GitHub repository.
5. In the Vercel project configuration:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend/`
   - **Environment Variables**: Add a new variable where:
     - Key = `VITE_API_URL`
     - Value = `https://<your-username>-sonar-shield-api.hf.space` (Your Hugging Face URL)
6. Click **Deploy**.

Vercel will give you a live, globally hosted HTTPS URL for your application. When a user uploads a Sonar image, the Vercel app will send it securely to your Hugging Face Space, which will process the fusion pipeline and return the results instantly.
