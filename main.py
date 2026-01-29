#ssm-video-engine main.py


import os
import time
import base64
import requests
import uuid
import json
from functions_framework import http
from google.cloud import storage

RUNPOD_API_KEY = os.environ["RUNPOD_API_KEY"]
RUNPOD_ENDPOINT_ID = os.environ["RUNPOD_ENDPOINT_ID"]
BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]

HEADERS = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json"
}

@http
def sdxl_manager(request):
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt")
    job_id = data.get("jobId")

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    # =========================
    # PHASE 1 — START JOB
    # =========================
    if not job_id:
        if not prompt:
            return {"status": "error", "message": "Missing prompt"}, 400

        payload = {
            "input": {
                "prompt": prompt,
                "num_inference_steps": 4
            }
        }

        res = requests.post(
            f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/run",
            headers=HEADERS,
            json=payload,
            timeout=5
        )
        res.raise_for_status()

        job_id = res.json()["id"]

        # Persist job state
        job_blob = bucket.blob(f"sdxl_jobs/{job_id}.json")
        job_blob.upload_from_string(json.dumps({
            "status": "PENDING",
            "prompt": prompt
        }))

        return {
            "status": "pending",
            "jobId": job_id
        }, 202

    # =========================
    # PHASE 2 — POLL JOB
    # =========================
    job_blob = bucket.blob(f"sdxl_jobs/{job_id}.json")
    if not job_blob.exists():
        return {"status": "error", "message": "Unknown jobId"}, 404

    job_state = json.loads(job_blob.download_as_text())

    # Already completed → return final result
    if job_state.get("status") == "COMPLETE":
        return {
            "status": "success",
            "public_url": job_state["public_url"]
        }, 200

    # Poll RunPod
    status_res = requests.get(
        f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/status/{job_id}",
        headers=HEADERS,
        timeout=90
    ).json()

    if status_res.get("status") == "FAILED":
        job_state["status"] = "FAILED"
        job_blob.upload_from_string(json.dumps(job_state))
        return {"status": "error", "message": "RunPod job failed"}, 500

    if status_res.get("status") != "COMPLETED":
        return {
            "status": "pending",
            "jobId": job_id
        }, 200

    # =========================
    # PHASE 3 — SAVE IMAGE
    # =========================
    # =========================
    # PHASE 3 — SAVE IMAGE
    # =========================
    images = status_res.get("output", {}).get("images", [])
    if not images or not isinstance(images, list):
        return {"status": "pending", "jobId": job_id}, 200
    
    first = images[0]
    
    # first may be a dict: {"image": "..."} OR a string: "data:image/png;base64,..."
    if isinstance(first, dict):
        image_str = first.get("image")
    elif isinstance(first, str):
        image_str = first
    else:
        return {"status": "pending", "jobId": job_id}, 200
    
    if not image_str or not isinstance(image_str, str):
        return {"status": "pending", "jobId": job_id}, 200
    
    # Strip optional data URL prefix
    if image_str.startswith("data:image"):
        image_str = image_str.split(",", 1)[1]
    
    image_bytes = base64.b64decode(image_str)


    safe_id = uuid.uuid4().hex[:8]
    filename = f"generated/sdxl_{safe_id}.png"

    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/png")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

    # Persist completion
    job_state["status"] = "COMPLETE"
    job_state["public_url"] = public_url
    job_blob.upload_from_string(json.dumps(job_state))

    return {
        "status": "success",
        "public_url": public_url
    }, 200
