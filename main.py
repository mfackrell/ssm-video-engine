#ssm-video-engine main.py

import os
import requests
from functions_framework import http
from google.cloud import storage

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")
BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

@http
def sdxl_manager(request):
    request_json = request.get_json(silent=True) or {}
    prompt = request_json.get("prompt", "beach twilight")
    job_id = request_json.get("jobId") # Orchestrator passes this if polling

    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"}

    # STEP 1: If no job_id, start the job
    if not job_id:
        payload = {"input": {"prompt": prompt, "num_inference_steps": 4}}
        res = requests.post(f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/run", headers=headers, json=payload)
        new_job_id = res.json().get("id")
        return {"state": "PENDING", "jobId": new_job_id}, 202

    # STEP 2: If we have a job_id, check status
    status_res = requests.get(f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/status/{job_id}", headers=headers).json()
    
    if status_res.get("status") == "COMPLETED":
        image_base64 = status_res["output"]["images"][0]["image"]
        
        # Save to GCS
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        filename = f"generated/{job_id}.png"
        blob = bucket.blob(filename)
        import base64
        blob.upload_from_string(base64.b64decode(image_base64), content_type="image/png")
        
        return {
            "state": "COMPLETE", 
            "imageUrl": f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        }, 200
    
    if status_res.get("status") in ["FAILED", "CANCELLED"]:
        return {"state": "FAILED"}, 500

    return {"state": "PENDING", "jobId": job_id}, 200
