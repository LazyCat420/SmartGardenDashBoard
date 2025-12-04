"""
Test script to validate LLM sorting with complex journal entry
"""
import requests
import json
from datetime import datetime

# First, add plants that match the journal entry
print("=" * 80)
print("Setting up test plants...")
print("=" * 80)

plants_to_add = [
    {
        "id": f"plant_tomato_{datetime.now().timestamp()}",
        "name": "Roma Tomatoes",
        "type": "Tomato",
        "variety": "Roma",
        "gridId": "grid_1",
        "quadrant": "A1",
        "dateAdded": datetime.now().isoformat(),
        "health": "healthy",
        "heightHistory": [],
        "healthHistory": [],
        "photos": [],
        "feedingRecipes": [],
        "feedingApplications": [],
        "journalEntries": []
    },
    {
        "id": f"plant_pepper_{datetime.now().timestamp()}",
        "name": "Bell Peppers",
        "type": "Pepper",
        "variety": "California Wonder",
        "gridId": "grid_1",
        "quadrant": "A2",
        "dateAdded": datetime.now().isoformat(),
        "health": "healthy",
        "heightHistory": [],
        "healthHistory": [],
        "photos": [],
        "feedingRecipes": [],
        "feedingApplications": [],
        "journalEntries": []
    }
]

for plant in plants_to_add:
    try:
        response = requests.post("http://localhost:5000/api/plants", json=plant)
        if response.status_code == 201:
            print(f"✅ Added plant: {plant['name']}")
        else:
            print(f"⚠️  Plant may already exist: {plant['name']}")
    except Exception as e:
        print(f"❌ Error adding plant: {e}")

print("\n" + "=" * 80)

# Complex journal entry with multiple plants
journal_entry = """
**Tomatoes (Roma & Cherry varieties):** Upper leaves showing physiological curl—likely heat/light stress [web:28][web:29]. Raised LED fixture 2" to reduce intensity. Fruit set visible on 3 Roma plants; Cherry variety producing clusters of 8-12 fruits per truss. Monitoring for blossom end rot.

**Basil (Genovese & Thai):** Dense, bushy growth on both cultivars. Genovese ready for third harvest—stems 8-10" with 6-8 leaf nodes. Thai basil showing purple flower buds; pinched terminal growth to promote lateral branching and delay bolting.

**Bell Peppers (California Wonder & Orange Sun):** First flowers appearing on two California Wonder specimens. Growth slower than expected but steady—plants 12-14" tall. Orange Sun still in vegetative phase.
"""

# Prepare the request
url = "http://localhost:5000/api/journal"
data = {
    "id": f"test_{datetime.now().timestamp()}",
    "date": datetime.now().isoformat(),
    "content": journal_entry,
    "processWithAI": True
}

print("Testing Complex Journal Entry with AI Processing")
print("=" * 80)
print("\nJournal Entry:")
print(journal_entry)
print("\n" + "=" * 80)
print("Sending to backend...")

try:
    response = requests.post(url, json=data)
    print(f"\nStatus: {response.status_code}")
    
    if response.status_code == 201:
        result = response.json()
        print("\n✅ SUCCESS - Journal entry processed")
        print("\n" + "=" * 80)
        print("Processed Data:")
        print("=" * 80)
        
        if 'processed_data' in result:
            processed = result['processed_data']
            
            print(f"\n📋 Plants Mentioned: {processed.get('plants_mentioned', [])}")
            print(f"\n🌱 Related Plant IDs: {result.get('relatedPlantIds', [])}")
            
            print(f"\n🎯 Actions Extracted ({len(processed.get('actions', []))}):")
            for i, action in enumerate(processed.get('actions', []), 1):
                print(f"\n  {i}. {action.get('action_type', 'unknown').upper()}")
                print(f"     Plant: {action.get('plant', 'N/A')}")
                if action.get('height'):
                    print(f"     Height: {action.get('height')} {action.get('unit', '')}")
                if action.get('details'):
                    print(f"     Details: {action.get('details')}")
                if action.get('amount'):
                    print(f"     Amount: {action.get('amount')}")
            
            print(f"\n📝 Summary: {processed.get('summary', 'N/A')}")
        
        print("\n" + "=" * 80)
        print("Full Response:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        
    else:
        print(f"\n❌ FAILED - Status {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("\n" + "=" * 80)
print("Now check the UI to verify:")
print("1. Plant Tracker shows updated height data")
print("2. Journal History displays the entry correctly")
print("3. Each plant's journal references the entry")
print("=" * 80)
