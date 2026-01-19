import os
import base64
import requests
import functions_framework
from google.cloud import storage

# Configure these in your GCF Environment Variables
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")
BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

@functions_framework.http
def generate_and_save(request):
    request_json = request.get_json(silent=True)
    prompt = request_json.get('prompt', 'A futuristic city at sunset')
    
    # 1. Call RunPod SDXL API
    url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/runsync"
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": {
            "prompt": prompt,
            "width": 1024,
            "height": 1024
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    
    # RunPod returns the image as a base64 string
    image_base64 = result['output'] # Adjust key based on specific template
    image_data = base64.b64decode(image_base64)

    # 2. Save to Google Cloud Storage
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"generated_images/{prompt.replace(' ', '_')[:20]}.png")
    
    blob.upload_from_string(image_data, content_type="image/png")

    return f"Image saved to gs://{BUCKET_NAME}/{blob.name}", 200
