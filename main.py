import os
import base64
import requests
from functions_framework import http
from google.cloud import storage

# Configure these in your Google Cloud Run Environment Variables
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")
BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

@http
def sdxl_manager(request):
    # Safe request handling: get json or default to empty dict
    request_json = request.get_json(silent=True) or {}
    prompt = request_json.get("prompt", "A high-end fractional CFO office")

    # 1. Call RunPod (Sync mode)
    url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/runsync"
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": {
            "prompt": prompt,
            "num_inference_steps": 4
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status() # Raises exception for 4xx/5xx errors
        result = response.json()

        # 2. Extract and Save Image
        image_base64 = result["output"][0]
        image_data = base64.b64decode(image_base64)

        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        
        # Create a safe filename from the first 15 chars of the prompt
        safe_name = prompt[:15].strip().replace(" ", "_")
        filename = f"generated/{safe_name}.png"
        blob = bucket.blob(filename)
        
        blob.upload_from_string(image_data, content_type="image/png")

        return {
            "status": "success",
            "gcs_path": f"gs://{BUCKET_NAME}/{filename}"
        }, 200

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500
