import os
import base64
import requests
import functions_framework
from google.cloud import storage

# Configure these in your Cloud Run / GCF Environment Variables
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")
BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

@functions_framework.http
def sdxl_manager(request):
    request_json = request.get_json(silent=True)
    # Default prompt if none is provided in the POST request
    prompt = request_json.get('prompt', 'A high-end fractional CFO office')
    
    # 1. Call RunPod (Sync mode)
    # Using RUNPOD_ENDPOINT_ID to match the variable above
    url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/runsync"
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"input": {"prompt": prompt, "num_inference_steps": 4}}
    
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    
    # 2. Extract and Save Image
    # SDXL-Turbo returns a list of images in base64; we take the first one
    try:
        image_base64 = result['output'][0] 
        image_data = base64.b64decode(image_base64)

        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        # Create a safe filename from the first 15 chars of the prompt
        filename = f"generated/{prompt[:15].replace(' ', '_')}.png"
        blob = bucket.blob(filename)
        
        blob.upload_from_string(image_data, content_type="image/png")

        return f"Success! Image saved to: gs://{BUCKET_NAME}/{filename}", 200
    except Exception as e:
        return f"Error processing image: {str(e)} | RunPod Result: {result}", 500
