import requests
import subprocess

# 1. PASTE YOUR SERVICE URL FROM GOOGLE CLOUD HERE
SERVICE_URL = "https://sdxl-manager-710616455963.us-central1.run.app"

def get_auth_token():
    """
    Generates an OIDC token using your local gcloud authentication.
    Ensure you have run 'gcloud auth login' first.
    """
    try:
        return subprocess.check_output(
            ["gcloud", "auth", "print-identity-token"]
        ).decode("utf-8").strip()
    except Exception as e:
        print(f"Error getting token: {e}. Are you logged into gcloud?")
        return None

def test_generation():
    token = get_auth_token()
    if not token:
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # This matches the 'prompt' your main.py is looking for
    data = {
        "prompt": "A modern, high-tech fractional CFO office with panoramic city views"
    }

    print(f"Triggering image generation at: {SERVICE_URL}...")
    
    try:
        response = requests.post(SERVICE_URL, json=data, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("\nCheck your Google Cloud Storage bucket to see the new image!")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    test_generation()
