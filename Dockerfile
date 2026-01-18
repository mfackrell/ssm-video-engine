FROM us-docker.pkg.dev/deeplearning-platform-release/gcr.io/pytorch-gpu.2-4:cu121-py311

WORKDIR /app

# Cache models inside the image
ENV HF_HOME=/models

# System deps + static ffmpeg support
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    xz-utils \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Static ffmpeg
RUN curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    | tar -xJ \
    && mv ffmpeg-*/ffmpeg /usr/local/bin/ffmpeg \
    && mv ffmpeg-*/ffprobe /usr/local/bin/ffprobe \
    && rm -rf ffmpeg-*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download models (Fixed syntax)
RUN python -c "from diffusers import DiffusionPipeline, StableVideoDiffusionPipeline; \
DiffusionPipeline.from_pretrained('stabilityai/sdxl-turbo', torch_dtype='auto'); \
StableVideoDiffusionPipeline.from_pretrained('stabilityai/stable-video-diffusion-img1-5-pruned', torch_dtype='auto')"

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
