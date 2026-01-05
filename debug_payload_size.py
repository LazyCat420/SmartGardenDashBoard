
import json
import os
import sys

# Mock imports/data to reconstruct the payload
GARDEN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_plant",
            "description": "Add a new plant to the garden. Use when the user mentions planting something new.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the plant"},
                    "variety": {"type": "string", "description": "The specific variety"},
                    "location": {"type": "string", "description": "Where the plant is located"},
                    "date_planted": {"type": "string", "description": "Date planted (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Additional notes"},
                    "quantity": {"type": "integer", "description": "Number of plants to add"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_watering",
            "description": "Log a watering event for a plant. If the user mentions using a compost tea or nutrient recipe (like 'veg compost tea', 'flower tea', etc.), extract the recipe name. The system will automatically match it to saved recipes and calculate ingredient costs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "amount_ml": {"type": "number", "description": "Amount in ml"},
                    "amount_value": {"type": "number", "description": "Amount in other units"},
                    "amount_unit": {"type": "string", "description": "Unit (ml, gallons, cups)"},
                    "method": {"type": "string", "description": "Watering method - use specific recipe name if a tea/recipe was mentioned (e.g., 'veg compost tea', 'flower compost tea'), otherwise use general method (watering can, hose, spray, soak)"},
                    "recipe_name": {"type": "string", "description": "Name of compost tea or nutrient recipe used if mentioned (e.g., 'veg compost tea', 'bloom tea', 'kelp tea'). System will fuzzy-match to saved recipes and auto-fill ingredients/costs."},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["plant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_fertilization",
            "description": "Log a fertilization event for a plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "fertilizer_type": {"type": "string", "description": "Type of fertilizer"},
                    "amount": {"type": "string", "description": "Amount applied (e.g., '2 tbsp', '1 cup')"},
                    "npk_ratio": {"type": "string", "description": "NPK ratio (e.g., '10-10-10')"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["plant_name", "fertilizer_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_harvest",
            "description": "Log a harvest from a plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "quantity": {"type": "number", "description": "Amount harvested"},
                    "unit": {"type": "string", "description": "Unit (kg, lbs, pieces, bunches)"},
                    "quality_rating": {"type": "integer", "description": "Quality 1-10"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["plant_name", "quantity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_growth",
            "description": "Log growth measurements for a plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "height_cm": {"type": "number", "description": "Height in cm"},
                    "width_cm": {"type": "number", "description": "Width in cm"},
                    "leaf_count": {"type": "integer", "description": "Number of leaves"},
                    "health_rating": {"type": "integer", "description": "Health 1-10"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["plant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "report_pest_issue",
            "description": "Report a pest or disease issue for a plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Affected plant"},
                    "pest_type": {"type": "string", "description": "Type of pest/disease"},
                    "severity": {"type": "string", "description": "mild, moderate, or severe"},
                    "treatment": {"type": "string", "description": "Treatment applied"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["plant_name", "pest_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a garden task or reminder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "task_type": {"type": "string", "description": "watering, fertilizing, pruning, harvesting, planting, pest_control, maintenance, other"},
                    "due_date": {"type": "string", "description": "Due date (YYYY-MM-DD)"},
                    "priority": {"type": "string", "description": "low, medium, high"},
                    "description": {"type": "string", "description": "Task details"},
                    "recurring": {"type": "boolean", "description": "Is this recurring?"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_weather",
            "description": "Log weather conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature_high": {"type": "number", "description": "High temp"},
                    "temperature_low": {"type": "number", "description": "Low temp"},
                    "humidity": {"type": "number", "description": "Humidity %"},
                    "rainfall_mm": {"type": "number", "description": "Rainfall mm"},
                    "conditions": {"type": "string", "description": "sunny, cloudy, rainy, etc."},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_plant_status",
            "description": "Update a plant's status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "status": {"type": "string", "description": "active, harvested, or removed"}
                },
                "required": ["plant_name", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_budget_item",
            "description": "Add a product/nutrient to budget tracking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Product name"},
                    "brand": {"type": "string", "description": "Brand name"},
                    "category": {"type": "string", "description": "fertilizer, amendment, pesticide, tool, seed, other"},
                    "size_amount": {"type": "number", "description": "Package size amount"},
                    "size_unit": {"type": "string", "description": "oz, lb, gallon, each"},
                    "purchase_price": {"type": "number", "description": "Purchase price"},
                    "npk_ratio": {"type": "string", "description": "NPK if applicable"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["name", "purchase_price"]
            }
        }
    }
]

recipe_names = ["Compost Tea", "Veg Tea"] # Mock
recipe_list = ", ".join(recipe_names)

system_prompt = f"""You are a helpful garden assistant that extracts ALL garden data from user notes.

CRITICAL INSTRUCTIONS FOR CATEGORIZING ACTIONS:
1. Extract EVERY piece of information from the note into the appropriate action type:
   - WATERING: Any mention of watering, using tea/recipe, irrigating. Use log_watering.
   - GROWTH: Any mention of height, size, health, appearance, looking sick/good. Use log_growth.
   - HARVEST: Any mention of picking, harvesting, collecting produce. Use log_harvest.
   - ISSUES/PESTS: Any mention of pests, disease, problems, wilting, overwatering damage. Use report_pest_issue.
   - STATUS UPDATES: Plant died, removed, finished. Use update_plant_status.

2. RECIPE MATCHING: When user mentions using a tea or recipe for watering:
   - Extract the recipe name exactly as mentioned (e.g., "veg compost tea", "flower tea", "bloom tea")
   - Put the recipe name in BOTH the 'method' and 'recipe_name' fields
   - Available recipes in the system: {recipe_list}
   - The system will automatically fuzzy-match to the closest recipe and calculate costs

3. SPLIT MULTIPLE OBSERVATIONS: A single sentence may contain MULTIPLE pieces of info:
   - "Water with veg compost tea. Plant is 12 inches tall now. Looks sick will stop overwatering."
   = log_watering (recipe_name: "veg compost tea") 
   + log_growth (height_cm: 30.48, notes: "12 inches tall")
   + report_pest_issue (pest_type: "overwatering damage", severity: "moderate", notes: "looks sick, will stop overwatering")

4. HEALTH DESCRIPTIONS map to health_rating (1-10):
   - "looking great/thriving/healthy" = 8-10
   - "doing okay/normal" = 5-7  
   - "not doing well/struggling" = 3-5
   - "looks sick/wilting/dying" = 1-3

5. Convert measurements: inches to cm (multiply by 2.54), feet to cm (multiply by 30.48)

6. When a plant has a variety (e.g., "Mint (Spearmint)"), include the variety in parentheses

Today's date is 2026-01-05
"""

payload = {
    "model": "granite-3.2-8b-instruct",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "add plant cherry tomato"}
    ],
    "tools": GARDEN_TOOLS,
    "tool_choice": "auto",
    "temperature": 0.7
}

json_str = json.dumps(payload)
print(f"Payload chars: {len(json_str)}")
print(f"System prompt chars: {len(system_prompt)}")
print(f"Tools chars: {len(json.dumps(GARDEN_TOOLS))}")
