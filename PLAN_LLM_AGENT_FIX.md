# Plan: Fix LLM Agent & Data Loading Issues

## Problem Analysis

### Issue 1: LLM Not Extracting/Categorizing Data Properly
**Symptom:** LLM creates generic summaries instead of structured extraction
**Current Output:** "General Notes: Tomatoes and Basil are showing signs of stress..."
**Expected Output:** Separate height measurements for C1=22.4", C2=21.9", feeding schedules with specific PPM values, watering amounts (750ml/48hrs), etc.

**Root Cause:** Current approach uses single-shot JSON extraction. LLM isn't acting as an agent—it's just summarizing. Needs to be using tool calling. Look online for examples. 

### Issue 2: Data Disappears on Tab Navigation
**Symptom:** Backend data loads initially, but when switching tabs (Plant Tracker → Journal → back to Plant Tracker), original sample data reappears
**Root Cause:** `initializeSampleData()` or `init()` being called multiple times, overwriting `appState`

### Issue 3: Plant Detail Tables Not Loading
**Errors:**
```
Cannot read properties of undefined (reading 'heightHistory')
Cannot read properties of undefined (reading 'feedingRecipes')
Cannot read properties of undefined (reading 'journalEntries')
Cannot read properties of undefined (reading 'photo')
Cannot read properties of null (reading 'toFixed') at line 3949
Cannot set properties of null (setting 'innerHTML') at line 6178
```

**Root Cause:** Plant objects missing expected fields or DOM elements don't exist when rendering

---

## Solution Strategy

### Phase 1: Fix Data Loading & Persistence (Critical)
**Priority:** HIGH - Blocks all other functionality

#### 1.1 Fix Null Reference Errors
- Add null checks before accessing `appliedCost.toFixed()`
- Check DOM elements exist before setting `innerHTML`
- Add defensive checks for undefined plant properties

#### 1.2 Fix Data Persistence
- Prevent `initializeSampleData()` from overwriting backend data
- Ensure `loadBackendData()` only runs once
- Add flag to track if backend data is loaded
- Remove any duplicate initialization calls

#### 1.3 Fix Plant Detail Rendering
- Ensure all plants have required fields (heightHistory, feedingRecipes, etc.)
- Parse JSON fields correctly from database
- Handle missing/null fields gracefully

---

### Phase 2: Implement LLM Tool Calling (Enhancement)
**Priority:** MEDIUM - Improves data extraction quality

#### 2.1 Research & Design
**Tool Calling Pattern:**
```python
# Define tools the LLM can call
tools = [
    {
        "name": "record_height_measurement",
        "description": "Record a plant's height measurement",
        "parameters": {
            "plant_name": "string",
            "position": "string (e.g., C1, A2)",
            "height": "number",
            "unit": "string (inches/cm)"
        }
    },
    {
        "name": "record_feeding",
        "description": "Record a feeding/fertilization event",
        "parameters": {
            "plant_name": "string",
            "fertilizer_name": "string",
            "npk_ratio": "string",
            "concentration": "string (ppm)",
            "date": "string"
        }
    },
    {
        "name": "record_watering",
        "description": "Record watering schedule",
        "parameters": {
            "plant_name": "string",
            "amount": "number",
            "unit": "string (ml/L)",
            "frequency": "string"
        }
    },
    {
        "name": "record_observation",
        "description": "Record observation about plant health/growth",
        "parameters": {
            "plant_name": "string",
            "category": "health|fruiting|flowering|growth",
            "observation": "string"
        }
    }
]
```

#### 2.2 Update LLM Service
**Current:** Single completion call → JSON output
**New:** Multi-turn conversation with tool calls

```python
def process_journal_entry_with_tools(text):
    messages = [
        {"role": "system", "content": AGENT_PROMPT},
        {"role": "user", "content": text}
    ]
    
    extracted_data = {
        "heights": [],
        "feedings": [],
        "waterings": [],
        "observations": []
    }
    
    # Allow LLM to make multiple tool calls
    max_iterations = 20
    for i in range(max_iterations):
        response = client.chat.completions.create(
            model="...",
            messages=messages,
            tools=tools,
            tool_choice="auto"  # Let LLM decide when to call tools
        )
        
        # Check if LLM wants to call a tool
        if response.choices[0].finish_reason == "tool_calls":
            tool_calls = response.choices[0].message.tool_calls
            
            for tool_call in tool_calls:
                # Execute tool and store data
                if tool_call.function.name == "record_height_measurement":
                    extracted_data["heights"].append(json.loads(tool_call.function.arguments))
                # ... handle other tools
            
            # Continue conversation with tool results
            messages.append(response.choices[0].message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": "Recorded successfully"
            })
        else:
            # LLM is done calling tools
            break
    
    return extracted_data
```

#### 2.3 Update Agent Prompt
**New Prompt Strategy:**
```
You are a meticulous garden data extraction agent. Your job is to analyze journal entries 
and use your tools to record EVERY piece of structured information.

PROCESS:
1. Read the journal entry carefully
2. Identify each plant mentioned with its position (e.g., "Cherry 'Sun Gold' at C1")
3. For EACH plant, call tools to record:
   - Height measurements (call record_height_measurement)
   - Feeding events (call record_feeding with NPK, PPM, date)
   - Watering schedules (call record_watering with amount, frequency)
   - Observations (call record_observation)

RULES:
- Make ONE tool call per distinct piece of information
- If entry says "C1=22.4", C2=21.9"" → make 2 separate height measurement calls
- Extract specific numeric values: PPM, ml, days, temperatures
- Extract dates and times when mentioned
- After extracting all data, call finish_extraction tool

EXAMPLE:
Input: "Fed yesterday (12/2) with MaxiGrow 10-5-14 at half strength (600ppm)"

Tool calls:
1. record_feeding(plant="Cherry Tomatoes", fertilizer="MaxiGrow", npk="10-5-14", 
   concentration="600ppm", date="2025-12-02")
```

---

## Implementation Steps

### Step 1: Fix Critical Data Loading Issues ⚠️
1. Add null checks in `getPlantExpandedContent()` line 3949
2. Add DOM existence checks before `innerHTML` assignments
3. Add `appState.__backendLoaded` flag to prevent re-initialization
4. Ensure JSON fields are parsed: `heightHistory`, `feedingApplications`, etc.

### Step 2: Fix Plant Detail Tables
1. Update `renderHeightHistoryTable()` to handle undefined plant
2. Update `renderFertilizationTable()` to handle undefined plant
3. Update `renderRecipesTable()` to handle undefined plant
4. Update `renderJournalTable()` to handle undefined plant
5. Update `renderPhotosTable()` to handle undefined plant

### Step 3: Implement LLM Tool Calling
1. Research LM Studio tool calling support
2. Define tool schemas in `llm_service.py`
3. Implement iterative tool calling loop
4. Update backend to process tool-extracted data
5. Test with complex Cherry Sun Gold entry

### Step 4: Validate & Test
1. Test tab navigation maintains data
2. Test plant details load correctly
3. Test complex journal entry extracts all data points
4. Verify height, feeding, watering data flows to correct sections

---

## Expected Outcomes

### Before Fix:
- ❌ "General Notes: Tomatoes and Basil showing signs..."
- ❌ Height: "Genovese Basil: 11.2inches" (single summary)
- ❌ Nutrients: Generic summaries
- ❌ Data disappears on tab switch
- ❌ Plant details fail to load

### After Fix:
- ✅ Separate height entries: C1=22.4", C2=21.9", Genovese=11.2", Thai=9.8", D1=13.2", D2=12.8", D3=11.4"
- ✅ Specific feeding records:
  - Cherry Tomatoes: MaxiGrow 10-5-14 @ 600ppm (12/2)
  - Basil: Fish Emulsion 5-1-1 every 7 days
  - Peppers: Dyna-Gro Bloom 3-12-6 @ 800ppm (11/28)
- ✅ Watering schedule: 750ml per plant every 48hrs
- ✅ Environmental data: Temps 70-73°F, considering raising to 75-78°F
- ✅ Data persists across tab navigation
- ✅ Plant details load without errors

---

## Files to Modify

1. **api.js** - Fix data persistence, prevent reinit
2. **index.html** - Add null checks in rendering functions (lines 3949, 4266, 4341, 4404, 4463, 6178)
3. **llm_service.py** - Implement tool calling architecture
4. **app.py** - Process tool-extracted data

---

## Testing Checklist

- [ ] Plant Tracker loads without errors
- [ ] Height history displays for each plant
- [ ] Feeding records display correctly
- [ ] Tab navigation preserves data
- [ ] Complex journal entry (Cherry Sun Gold) extracts:
  - [ ] 7 height measurements
  - [ ] 3 feeding schedules with NPK + PPM
  - [ ] Watering schedule (750ml/48hrs)
  - [ ] Temperature observations
  - [ ] Growth observations
  - [ ] Harvest data (42g fresh weight)
