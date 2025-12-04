import requests
import json

# Test the LLM processing endpoint
url = "http://localhost:5000/api/llm/process-journal"

test_entry = "Watered the tomatoes today and added 5ml of CalMag. The basil is now 30cm tall."

response = requests.post(url, json={"text": test_entry})

print("Status Code:", response.status_code)
print("\nResponse:")
print(json.dumps(response.json(), indent=2))
