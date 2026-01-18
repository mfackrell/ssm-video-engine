FROM us-docker.pkg.dev/deeplearning-platform-release/gcr.io/pytorch-gpu.2-4.py311

WORKDIR /app

# Stable HuggingFace cache location
ENV HF_HOME=/models

# System dependencies for FFmpeg processing
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 && rm -rf /var/lib/apt/lists/*

# Install pinned Python libraries
RUN pip install --no-cache-dir \
    fastapi uvicorn diffusers==0.27.2 accelerate transformers \
    opencv-python google-cloud-storage pillow safetensors

# Pre-download SDXL Turbo + Stable Video Diffusion during build
RUN python -c "from diffusers import DiffusionPipeline, StableVideoDiffusionPipeline; \
    DiffusionPipeline.from_pretrained('stabilityai/sdxl-turbo', torch_d
