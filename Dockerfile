FROM us-docker.pkg.dev/deeplearning-platform-release/gcr.io/pytorch-gpu.2-4.py310

WORKDIR /app

ENV HF_HOME=/models
ENV TOKENIZERS_PARALLELISM=false

RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG HF_TOKEN
RUN python - <<EOF
from diffusers import StableVideoDiffusionPipeline
StableVideoDiffusionPipeline.from_pretrained(
  "stabilityai/stable-video-diffusion-img1-5",
  use_auth_token="$HF_TOKEN"
)
EOF

COPY run_svd_frames.py .

CMD ["python", "run_svd_frames.py"]
