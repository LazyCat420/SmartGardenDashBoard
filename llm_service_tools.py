from openai import OpenAI
import json

# Configure to point to local LM Studio instance
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# Define tools that the LLM can call to structure garden data
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "record_height_measurement",
            "description": "Record a plant's height measurement. Call this for EACH individual plant mentioned with a height value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "Full plant name including variety (e.g., 'Cherry Sun Gold Tomatoes', 'Genovese Basil')"
                    },
                    "position": {
                        "type": "string",
                        "description": "Position identifier if mentioned (e.g., 'C1', 'A2', 'D1')"
                    },
                    "height": {
                        "type": "number",
                        "description": "Numeric height value"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["inches", "cm", "mm", "feet"],
                        "description": "Unit of measurement"
                    },
                    "details": {
                        "type": "string",
                        "description": "Additional context about the measurement"
                    }
                },
                "required": ["plant_name", "height", "unit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_feeding",
            "description": "Record a feeding/fertilization event. Call this for EACH distinct feeding mentioned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "Full plant name including variety"
                    },
                    "fertilizer_name": {
                        "type": "string",
                        "description": "Name/brand of fertilizer (e.g., 'MaxiGrow', 'Fish Emulsion')"
                    },
                    "npk_ratio": {
                        "type": "string",
                        "description": "NPK ratio if mentioned (e.g., '10-5-14', '5-1-1')"
                    },
                    "concentration": {
                        "type": "string",
                        "description": "Concentration in PPM or percentage if mentioned"
                    },
                    "amount": {
                        "type": "string",
                        "description": "Amount applied if mentioned"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of feeding if mentioned (e.g., '12/2', '11/30')"
                    },
                    "frequency": {
                        "type": "string",
                        "description": "Feeding frequency if mentioned (e.g., 'every 7 days')"
                    },
                    "details": {
                        "type": "string",
                        "description": "Additional notes about the feeding"
                    }
                },
                "required": ["plant_name", "fertilizer_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_watering",
            "description": "Record watering schedule or event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "Full plant name"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Water amount as number"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit (ml, L, gallons, etc.)"
                    },
                    "frequency": {
                        "type": "string",
                        "description": "Watering frequency (e.g., 'every 48hrs', 'daily')"
                    },
                    "details": {
                        "type": "string",
                        "description": "Additional watering notes"
                    }
                },
                "required": ["plant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_observation",
            "description": "Record an observation about plant health, growth, fruiting, flowering, or pests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "Full plant name"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["health", "fruiting", "flowering", "growth", "pest", "disease", "general"],
                        "description": "Type of observation"
                    },
                    "observation": {
                        "type": "string",
                        "description": "The observation details"
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["positive", "neutral", "moderate", "critical"],
                        "description": "Severity or status"
                    }
                },
                "required": ["plant_name", "category", "observation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_environmental_change",
            "description": "Record environmental adjustments like lighting, temperature, humidity changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "Plant affected by the change"
                    },
                    "change_type": {
                        "type": "string",
                        "enum": ["lighting", "temperature", "humidity", "ventilation"],
                        "description": "Type of environmental change"
                    },
                    "current_value": {
                        "type": "string",
                        "description": "Current environmental value"
                    },
                    "target_value": {
                        "type": "string",
                        "description": "Target or desired value"
                    },
                    "action_taken": {
                        "type": "string",
                        "description": "What action was taken"
                    },
                    "details": {
                        "type": "string",
                        "description": "Additional context"
                    }
                },
                "required": ["change_type", "details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_pruning",
            "description": "Record pruning or trimming action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "Plant that was pruned"
                    },
                    "pruning_type": {
                        "type": "string",
                        "enum": ["topping", "thinning", "deadheading", "pinching", "shaping"],
                        "description": "Type of pruning"
                    },
                    "time": {
                        "type": "string",
                        "description": "Time of pruning if mentioned"
                    },
                    "details": {
                        "type": "string",
                        "description": "Pruning details"
                    }
                },
                "required": ["plant_name", "details"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_harvest_data",
            "description": "Record harvest information including yield, weight, quality.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "Plant harvested from"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount harvested"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit (grams, oz, count, etc.)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of harvest"
                    },
                    "quality": {
                        "type": "string",
                        "description": "Quality notes"
                    },
                    "details": {
                        "type": "string",
                        "description": "Additional harvest details"
                    }
                },
                "required": ["plant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finish_extraction",
            "description": "Call this when you have finished extracting all structured data from the journal entry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "EXTREMELY CONCISE summary (max 15 words) of key events. Do NOT list details extracted elsewhere."
                    },
                    "plants_mentioned": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of all plant names mentioned"
                    }
                },
                "required": ["summary", "plants_mentioned"]
            }
        }
    }
]

AGENT_SYSTEM_PROMPT = """You are a smart garden journal sorter. Your ONLY job is to extract data using the provided tools.
DO NOT output JSON or text directly. You MUST use the function calls.
If you output any conversational text, the system will fail.

NEGATIVE CONSTRAINTS:
- DO NOT say "Here is the extracted data".
- DO NOT say "I have processed the journal".
- DO NOT output markdown blocks like ```json ... ```.
- DO NOT make up data that is not in the text.

1. CORE BEHAVIOR
- Extract data, not prose.
- Support multiple plants and multiple events per plant.
- NEVER chat with the user. ONLY call tools.

2. PLANT NAME RULES (CRITICAL):
- ALWAYS split compound plant names into SEPARATE tool calls.
- "Bell Peppers (California Wonder & Orange Sun)" = TWO plants: "California Wonder Bell Pepper" and "Orange Sun Bell Pepper"
- "Basil (Genovese & Thai)" = TWO plants: "Genovese Basil" and "Thai Basil"
- "Tomatoes (Roma & Cherry)" = TWO plants: "Roma Tomatoes" and "Cherry Tomatoes"
- Each variety MUST be a separate tool call with its own data.
- Format: "[Variety] [Type]" e.g. "California Wonder Bell Pepper", "Genovese Basil", "Roma Tomatoes"

3. DATA TO CAPTURE (Use these tools):
- `record_height_measurement`: Height, width, canopy diameter. MUST include numeric height value.
- `record_feeding`: Fertilizer type, NPK, PPM, dates.
- `record_watering`: Amounts and frequency.
- `record_observation`: Health notes (leaf curl, yellowing), status, pests.
- `record_environmental_change`: Temp/humidity/light changes.
- `record_pruning`: Topping, pinching, trimming.
- `record_harvest_data`: Yields, weights.
- `finish_extraction`: Call this LAST with a VERY CONCISE summary (max 15 words).

4. EXTRACTION RULES
- Identity: Capture plant name, type, variety, and position (C1, A2, D1, etc).
- If heights given as "D1=13.2, D2=12.8", make TWO calls with positions D1 and D2.
- Status: Capture current size, age, health.
- Missing Data: If a field is not stated, leave it null/empty. Do not guess.
- Noise: Ignore random notes ("coffee was strong", "reminder: check neighbor").

5. CRITICAL INSTRUCTIONS
- Make ONE tool call per distinct piece of information per plant.
- SPLIT compound entries: "California Wonder & Orange Sun" = 2 separate tool calls.
- If "all tomatoes" mentioned, use plant_name="all tomatoes" (backend will expand).
- If specific variety mentioned, use that variety name.
- Call `finish_extraction` only when ALL data has been recorded.
"""


def process_journal_entry(text):
    """
    Process journal entry using tool calling to extract structured data.
    The LLM will make multiple tool calls to systematically extract all information.
    """
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": f"Extract all structured data from this journal entry:\n\n{text}"}
    ]
    
    # Storage for extracted data
    extracted_data = {
        "heights": [],
        "feedings": [],
        "waterings": [],
        "observations": [],
        "environmental_changes": [],
        "prunings": [],
        "harvests": [],
        "summary": "",
        "plants_mentioned": []
    }
    
    # Allow model to make multiple tool calls (up to 50 for complex entries)
    max_iterations = 50
    
    try:
        for iteration in range(max_iterations):
            response = client.chat.completions.create(
                model="ibm-granite_granite-3.3-8b-instruct",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",  # Let model decide when to call tools
                temperature=0.0,  # Zero temperature for strict extraction
                max_tokens=-1
            )
            
            response_message = response.choices[0].message
            
            # Check if model wants to call tools
            if response.choices[0].finish_reason == "tool_calls" and response_message.tool_calls:
                # Append assistant message
                messages.append(response_message.model_dump())
                
                # Process each tool call
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"[Tool Call {iteration}] {function_name}: {function_args}")
                    
                    # Store the extracted data
                    if function_name == "record_height_measurement":
                        extracted_data["heights"].append(function_args)
                    elif function_name == "record_feeding":
                        extracted_data["feedings"].append(function_args)
                    elif function_name == "record_watering":
                        extracted_data["waterings"].append(function_args)
                    elif function_name == "record_observation":
                        extracted_data["observations"].append(function_args)
                    elif function_name == "record_environmental_change":
                        extracted_data["environmental_changes"].append(function_args)
                    elif function_name == "record_pruning":
                        extracted_data["prunings"].append(function_args)
                    elif function_name == "record_harvest_data":
                        extracted_data["harvests"].append(function_args)
                    elif function_name == "finish_extraction":
                        extracted_data["summary"] = function_args.get("summary", "")
                        extracted_data["plants_mentioned"] = function_args.get("plants_mentioned", [])
                        # Model indicates it's done
                        print(f"Extraction complete after {iteration + 1} iterations")
                        return {
                            "success": True,
                            "extracted_data": extracted_data,
                            "raw_text": text
                        }
                    
                    # Append tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps({"status": "recorded", "data": function_args})
                    })
            else:
                # Model is done (no more tool calls)
                if not extracted_data["summary"]:
                    print("Model stopped without summary. Forcing finish_extraction...")
                    messages.append({"role": "user", "content": "You have recorded the data. Now you MUST call finish_extraction."})
                    continue
                
                print(f"Model finished without calling finish_extraction (iteration {iteration + 1})")
                break
        
        # If we reach here, extraction is complete
        return {
            "success": True,
            "extracted_data": extracted_data,
            "raw_text": text
        }
        
    except Exception as e:
        print(f"Error in tool calling: {e}")
        return {
            "success": False,
            "extracted_data": extracted_data,
            "error": str(e),
            "raw_text": text
        }
