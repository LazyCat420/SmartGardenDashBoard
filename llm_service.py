from openai import OpenAI
import json

# Configure to point to local LM Studio instance
# Standard LM Studio port is 1234
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

def process_journal_entry(text):
    """
    Sends the journal text to the local LLM to extract structured data.
    """
    
    system_prompt = """
    You are a gardening data extraction assistant. Your task is to parse journal entries into structured data for automated form filling.
    
    CRITICAL RULES:
    1. Extract COMPLETE plant names including varieties (e.g., "Roma Tomatoes", "Cherry Tomatoes", "Genovese Basil", "Thai Basil")
    2. Each variety mentioned should be a separate plant entity
    3. Extract ALL numeric measurements with units
    4. Categorize every observation and action clearly
    5. Return ONLY valid JSON, no markdown formatting
    
    INPUT FORMAT: Natural language garden journal entry
    OUTPUT FORMAT: Structured JSON with these exact fields:
    
    {
        "plants_mentioned": [
            "Roma Tomatoes",
            "Cherry Tomatoes",
            "Genovese Basil",
            "Thai Basil",
            "California Wonder Bell Peppers",
            "Orange Sun Bell Peppers"
        ],
        "actions": [
            {
                "action_type": "height_measurement",
                "plant": "Genovese Basil",
                "height": 9,
                "unit": "inches",
                "details": "Stems 8-10 inches with 6-8 leaf nodes"
            },
            {
                "action_type": "observation",
                "plant": "Roma Tomatoes",
                "category": "health",
                "severity": "moderate",
                "details": "Upper leaves showing physiological curl from heat/light stress"
            },
            {
                "action_type": "observation",
                "plant": "Roma Tomatoes",
                "category": "fruiting",
                "severity": "positive",
                "details": "Fruit set visible on 3 plants"
            },
            {
                "action_type": "observation",
                "plant": "Cherry Tomatoes",
                "category": "fruiting",
                "severity": "positive",
                "details": "Producing clusters of 8-12 fruits per truss"
            },
            {
                "action_type": "environmental_adjustment",
                "plant": "Roma Tomatoes",
                "adjustment_type": "lighting",
                "details": "Raised LED fixture 2 inches to reduce intensity"
            },
            {
                "action_type": "pruning",
                "plant": "Thai Basil",
                "pruning_type": "topping",
                "details": "Pinched terminal growth to promote lateral branching and delay bolting"
            },
            {
                "action_type": "feeding",
                "plant": "Plant Name",
                "nutrient_type": "fertilizer name or type",
                "amount": "5",
                "unit": "ml",
                "details": "Additional context"
            }
        ],
        "summary": "Brief 1-2 sentence overview of all activities"
    }
    
    ACTION TYPES:
    - height_measurement: Any growth measurements (include height, unit)
    - observation: Visual checks, health status, pest/disease notes (include category: health|fruiting|flowering|growth|pest, severity: positive|neutral|moderate|critical)
    - feeding: Fertilizer/nutrient applications (include nutrient_type, amount, unit)
    - watering: Water applications (include amount, unit if specified)
    - pruning: Any cutting/trimming (include pruning_type: topping|thinning|deadheading|shaping)
    - harvesting: Picking produce
    - environmental_adjustment: Changes to light, temperature, humidity (include adjustment_type: lighting|temperature|humidity|ventilation)
    - planting: New plants added
    
    EXTRACTION RULES:
    - If text says "Tomatoes (Roma & Cherry varieties)" extract BOTH "Roma Tomatoes" AND "Cherry Tomatoes"
    - If text says "Basil (Genovese & Thai)" extract BOTH "Genovese Basil" AND "Thai Basil"
    - If text says "Bell Peppers (California Wonder & Orange Sun)" extract BOTH as separate plants
    - Convert measurement ranges to averages: "8-10 inches" → 9 inches
    - Convert measurements: maintain original unit or convert to metric if requested
    - Split compound observations into separate action objects
    - Each distinct observation about a plant gets its own action entry
    
    RETURN ONLY THE JSON OBJECT, NO MARKDOWN CODE BLOCKS OR FORMATTING.
    """
    
    try:
        response = client.chat.completions.create(
            model="ibm-granite_granite-3.3-8b-instruct",  # Your LM Studio model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=-1,
            stream=False
        )
        
        content = response.choices[0].message.content
        
        # Cleanup for potential markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        parsed = json.loads(content)
        
        # Post-process: If any observation has height/unit, convert to height_measurement
        if 'actions' in parsed:
            for action in parsed['actions']:
                if action.get('action_type') == 'observation' and 'height' in action:
                    action['action_type'] = 'height_measurement'
                    # Remove observation-specific fields
                    action.pop('category', None)
                    action.pop('severity', None)
        
        return {
            "success": True,
            "processed_data": parsed,
            "raw_text": text
        }
        
    except Exception as e:
        print(f"Error calling LLM: {e}")
        # Fallback or re-raise
        return {
            "success": False,
            "processed_data": {
                "plants_mentioned": [],
                "actions": [],
                "summary": text
            },
            "error": str(e),
            "raw_text": text
        }
