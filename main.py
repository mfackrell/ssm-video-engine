//ssm-video-engine main.py

import os
import time
import base64
import requests
from functions_framework import http
from google.cloud import storage
import uuid


# Environment variables from your console
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")
BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

@http
def sdxl_manager(request):
    request_json = request.get_json(silent=True) or {}
    prompt = request_json.get("prompt", "a beach scene at twilight with footsteps on the sand, sun setting")

    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"input": {"prompt": prompt, "num_inference_steps": 4}}

    try:
        # 1. Submit RunPod job
        submit_url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/run"
        submit_response = requests.post(submit_url, headers=headers, json=payload, timeout=30)
        submit_response.raise_for_status()
        job_id = submit_response.json().get("id")

        # 2. Poll job status
        status_url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/status/{job_id}"
        image_base64 = None

        for _ in range(30):
            status_res = requests.get(status_url, headers=headers, timeout=10).json()
            
            if status_res.get("status") == "COMPLETED":
                # SURGICAL FIX: SDXL returns output['images'][0]['image']
                output = status_res.get("output", {})
                images = output.get("images", [])
                
                if not images or "image" not in images[0]:
                    return {"status": "error", "message": "No image in payload"}, 500
                
                image_base64 = images[0]["image"]
                break
            
            if status_res.get("status") == "FAILED":
                return {"status": "error", "message": "RunPod job failed"}, 500
            
            time.sleep(2)

        if not image_base64:
            return {"status": "error", "message": "Timed out"}, 504

        # 3. Save to GCS and return URL
        image_data = base64.b64decode(image_base64)
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        
        safe_name = prompt[:15].strip().replace(" ", "_")
        unique_id = uuid.uuid4().hex[:8]
        filename = f"generated/{safe_name}_{unique_id}.png"
        
        blob = bucket.blob(filename)
        blob.upload_from_string(image_data, content_type="image/png")

        return {
            "status": "success",
            "public_url": f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        }, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
