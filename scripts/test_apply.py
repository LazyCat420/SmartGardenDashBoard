
import requests
import json

def test_apply():
    url = "http://localhost:5000/api/llm/apply-actions"
    payload = {
        "actions": [
            {
                "action": "log_watering",
                "parameters": {
                    "plant_name": "Tomatoes",
                    "amount_ml": 500,
                    "date": "2026-01-04",
                    "notes": "Test watering"
                }
            },
            {
                "action": "log_growth",
                "parameters": {
                    "plant_name": "tomatoes",
                    "height_cm": 50,
                    "date": "2026-01-04",
                    "notes": "Test growth"
                }
            }
        ]
    }
    

    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        print(f"Status: {response.status_code}")
        print(response.text)
        
        # Verify persistence
        print("\nVerifying persistence...")
        plants_resp = requests.get("http://localhost:5000/api/plants")
        plants = plants_resp.json()
        
        found = False
        for p in plants:
            if "tomato" in p.get("name", "").lower():
                print(f"Checking plant: {p.get('name')} ({p.get('id')})")
                print(f"Waterings: {len(p.get('waterings', []))}")
                print(f"Growth Logs: {len(p.get('growth_logs', []))}")
                found = True
        
        if not found:
            print("No tomato plant found in list!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_apply()
