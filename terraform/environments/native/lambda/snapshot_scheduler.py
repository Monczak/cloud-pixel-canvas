import os
import json
import urllib.request
import urllib.error

def handler(event, context):
    api_url = os.environ.get("API_URL")
    if not api_url:
        raise ValueError("API_URL environment variable not set")
        
    api_url = api_url.rstrip("/")
    endpoint = f"{api_url}/api/canvas/snapshot"
    
    system_key = os.environ.get("SYSTEM_KEY")
    if not system_key:
        raise ValueError("SYSTEM_KEY environment variable not set")

    print(f"Triggering snapshot at {endpoint}...")

    req = urllib.request.Request(
        endpoint, 
        method="POST",
        headers={
            "Authorization": f"Bearer {system_key}",
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            body = response.read().decode()
            print(f"Snapshot triggered successfully. Status: {status}")
            return {
                "statusCode": status,
                "body": json.loads(body)
            }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"Response: {err_body}")
        raise e
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise e
