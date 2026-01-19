import os
import time
import base64
import requests
from functions_framework import http
from google.cloud import storage

# Required environment variables
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")
BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

@http
def sdxl_manager(request):
    # --- Validate environment ---
    if not RUNPOD_API_KEY or not RUNPOD_ENDPOINT_ID or not BUCKET_NAME:
        return {
            "status": "error",
            "message": "Missing required environment variables"
        }, 500

    # --- Parse request ---
    request_json = request.get_json(silent=True) or {}
    prompt = request_json.get("prompt", "A high-end fractional CFO office")

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
        # --- 1. Submit RunPod job (ASYNC) ---
        submit_url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/run"
        submit_response = requests.post(
            submit_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        submit_response.raise_for_status()
        submit_result = submit_response.json()

        job_id = submit_result.get("id")
        if not job_id:
            return {
                "status": "error",
                "message": "RunPod did not return a job ID",
                "response": submit_result
            }, 500

        # --- 2. Poll job status ---
        status_url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/status/{job_id}"

        image_base64 = None

        for _ in range(30):  # ~60 seconds max (30 * 2s)
            status_response = requests.get(
                status_url,
                headers=headers,
                timeout=10
            )
            status_response.raise_for_status()
            status_result = status_response.json()

            job_status = status_result.get("status")

            if job_status == "COMPLETED":
                output = status_result.get("output")
                
                if not output:
                    return {
                        "status": "error",
                        "message": "RunPod job completed but no output returned",
                        "response": status_result
                    }, 500
                
                # RunPod may return a single base64 string OR a list
                if isinstance(output, list):
                    image_base64 = output[0]
                elif isinstance(output, str):
                    image_base64 = output
                else:
                    return {
                        "status": "error",
                        "message": "Unexpected RunPod output format",
                        "response": status_result
                    }, 500

                break

            if job_status == "FAILED":
                return {
                    "status": "error",
                    "message": "RunPod job failed",
                    "response": status_result
                }, 500

            time.sleep(2)

        if not image_base64:
            return {
                "status": "error",
                "message": "RunPod job timed out"
            }, 504

        # --- 3. Save image to GCS ---
        image_data = base64.b64decode(image_base64)

        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)

        safe_name = prompt[:15].strip().replace(" ", "_")
        filename = f"generated/{safe_name}.png"

        blob = bucket.blob(filename)
        blob.upload_from_string(image_data, content_type="image/png")

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        # --- 4. Success ---
        return {
            "status": "success",
            "job_id": job_id,
            "gcs_path": f"gs://{BUCKET_NAME}/{filename}",
            "public_url": public_url
        }, 200

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500
