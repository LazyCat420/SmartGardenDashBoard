import requests, json

url = 'http://localhost:5000/api/journal'

payload = {
    'date': '2025-12-03',
    'content': 'Watered the tomatoes and fed with compost. Basil is 30cm',
    'processWithAI': True
}

r = requests.post(url, json=payload)
print('status', r.status_code)
try:
    print('response', json.dumps(r.json(), indent=2))
except Exception as e:
    print('no json body', r.text)
