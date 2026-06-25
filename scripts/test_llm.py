
import requests
import json

def test_endpoint(name, url, payload):
    print(f"\n--- Testing {name} ---")
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        print(f"Status: {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

test_endpoint("Values", "http://localhost:5000/api/llm/process-note", {"note": "Water tomato"})
test_endpoint("Tools", "http://localhost:5000/api/llm/test-tools", {"note": "test"})
