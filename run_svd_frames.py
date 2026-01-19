import os
import sys
import tempfile
from pathlib import Path

import torch
from PIL import Image
from google.cloud import storage
from diffusers import StableVideoDiffusionPipeline


WIDTH = 576
HEIGHT = 1024
NUM_FRAMES = 24
FPS = 12


def require_env(name):
    v = os.getenv(name)
    if not v:
        print(f"Missing env var: {name}", file=sys.stderr)
        sys.exit(1)
    return v


def parse_gs(uri):
    assert uri.startswith("gs://")
    b, _, p = uri[5:].partition("/")
    return b, p


def main():
    input_gs = require_env("INPUT_GS_URI")
    output_gs = require_env("OUTPUT_GS_PREFIX")

    client = storage.Client()

    in_bucket, in_blob = parse_gs(input_gs)
    out_bucket, out_prefix = parse_gs(output_gs)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        input_path = td / "input.png"
        client.bucket(in_bucket).blob(in_blob).download_to_filename(input_path)

        image = Image.open(input_path).convert("RGB")
        image = image.resize((WIDTH, HEIGHT), Image.LANCZOS)

        pipe = StableVideoDiffusionPipeline.from_pretrained(
            "stabilityai/stable-video-diffusion-img1-5",
            torch_dtype=torch.float16,
            variant="fp16"
        ).to("cuda")

        pipe.enable_model_cpu_offload()

        result = pipe(
            image,
            num_frames=NUM_FRAMES,
            fps=FPS,
            motion_bucket_id=127,
            noise_aug_strength=0.02
        )

        frames = result.frames[0]
        bucket = client.bucket(out_bucket)

        for i, frame in enumerate(frames, 1):
            p = td / f"{i:04d}.png"
            frame.save(p)
            bucket.blob(f"{out_prefix}/frames/{i:04d}.png").upload_from_filename(p)

        bucket.blob(f"{out_prefix}/_SUCCESS").upload_from_string("ok")


if __name__ == "__main__":
    main()
