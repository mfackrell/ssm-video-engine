import os
import uuid
import hashlib
import torch
from fastapi import FastAPI
from diffusers import DiffusionPipeline, StableVideoDiffusionPipeline
from diffusers.utils import export_to_video
from google.cloud import storage
from PIL import Image

app = FastAPI()

# Load models once at startup (GPU warm)
sdxl_pipe = DiffusionPipeline.from_pretrained(
    "stabilityai/sdxl-turbo",
    torch_dtype=torch.float16,
    variant="fp16"
).to("cuda")

svd_pipe = StableVideoDiffusionPipeline.from_pretrained(
    "stabilityai/stable-video-diffusion-img1-5-pruned",
    torch_dtype=torch.float16,
    variant="fp16"
).to("cuda")


@app.post("/generate")
async def generate(payload: dict):
    mood = payload.get("mood", "calm minimalist workspace, soft light")

    # Deterministic but varied seed per mood
    seed = int(hashlib.sha256(mood.encode()).hexdigest(), 16) % (2**32)
    generator = torch.manual_seed(seed)

    # ---- STEP 1: Text → Image (SDXL Turbo, native 1024x1024) ----
    image_1024 = sdxl_pipe(
        prompt=mood,
        guidance_scale=1.0,
        num_inference_steps=4,
        height=1024,
        width=1024,
        generator=generator
    ).images[0]

    # ---- STEP 2: Center crop to vertical 9:16 (576x1024) ----
    image_vertical = image_1024.crop((224, 0, 800, 1024))

    # ---- STEP 3: Image → Video (Stable Video Diffusion) ----
    motion_bucket = 96 + (seed % 64)

    frames = svd_pipe(
        image_vertical,
        decode_chunk_size=8,
        generator=generator,
        num_frames=14,
        motion_bucket_id=motion_bucket
    ).frames[0]

    # ---- STEP 4: Export MP4 ----
    filename = f"ssm_bg_{uuid.uuid4()}.mp4"
    temp_path = f"/tmp/{filename}"
    export_to_video(frames, temp_path, fps=7)

    # ---- STEP 5: Upload to GCS ----
    bucket_name = os.environ.get("GCS_BUCKET")
    if not bucket_name:
        raise RuntimeError("GCS_BUCKET env var not set")

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"backgrounds/{filename}")
    blob.upload_from_filename(temp_path)

    if os.path.exists(temp_path):
        os.remove(temp_path)

    return {
        "url": f"https://storage.googleapis.com/{bucket_name}/backgrounds/{filename}"
    }
