"""
LLM Service for Smart Garden Dashboard
Uses LMStudio local API with tool calling to extract garden data from natural language notes
"""

import requests
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configure logging for LLM debugging
logging.basicConfig(level=logging.DEBUG)
llm_logger = logging.getLogger('llm_service')
llm_logger.setLevel(logging.DEBUG)

# Create file handler for detailed logs
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'llm_debug.log')
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
llm_logger.addHandler(file_handler)

# Settings file path
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'llm_settings.json')

# Default LMStudio API configuration
DEFAULT_LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"

# Prism (the shared AI gateway) attributes every request by the x-project /
# x-username HTTP HEADERS — it ignores project/username sent in the JSON body.
# Requests without them are filed under prism's catch-all "default"/"anonymous"
# project. The configured LLM URL can point at prism (LLM_SERVICE_URL in
# docker-compose.yml is http://10.0.0.16:7778/chat), so every outbound LLM call
# sends these; non-prism endpoints simply ignore the extra headers.
PRISM_PROJECT = os.environ.get("PRISM_PROJECT", "smart-garden")
PRISM_USERNAME = os.environ.get("PRISM_USERNAME", "admin")
PRISM_ATTRIBUTION_HEADERS = {
    "x-project": PRISM_PROJECT,
    "x-username": PRISM_USERNAME,
}
DEFAULT_MODEL_NAME = "ibm-granite/granite-3.3-8b-instruct"
DEFAULT_CONTEXT_LENGTH = 8192
DEFAULT_GPU_LAYERS = 35
DEFAULT_CPU_THREADS = 8

def load_llm_settings() -> Dict[str, Any]:
    """Load LLM settings from file or return defaults."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                llm_logger.info(f"Loaded settings from {SETTINGS_FILE}: {settings}")
                return settings
    except Exception as e:
        llm_logger.error(f"Error loading settings: {e}")
    
    return {
        "url": DEFAULT_LMSTUDIO_URL,
        "model": DEFAULT_MODEL_NAME,
        "api_key": "",
        "endpoint_type": "lmstudio",
        "context_length": DEFAULT_CONTEXT_LENGTH,
        "gpu_layers": DEFAULT_GPU_LAYERS,
        "cpu_threads": DEFAULT_CPU_THREADS
    }

def save_llm_settings(url: str, model: str, api_key: str = "", endpoint_type: str = "lmstudio", context_length: int = None, 
                      gpu_layers: int = None, cpu_threads: int = None) -> bool:
    """Save LLM settings to file."""
    try:
        settings = {
            "url": url, 
            "model": model,
            "api_key": api_key,
            "endpoint_type": endpoint_type
        }
        if context_length is not None:
            settings["context_length"] = context_length
        if gpu_layers is not None:
            settings["gpu_layers"] = gpu_layers
        if cpu_threads is not None:
            settings["cpu_threads"] = cpu_threads
        
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        llm_logger.info(f"Saved settings: {settings}")
        return True
    except Exception as e:
        llm_logger.error(f"Error saving settings: {e}")
        return False

# Load current settings
_settings = load_llm_settings()
LMSTUDIO_URL = _settings.get("url", DEFAULT_LMSTUDIO_URL)
MODEL_NAME = _settings.get("model", DEFAULT_MODEL_NAME)
API_KEY = _settings.get("api_key", "")
ENDPOINT_TYPE = _settings.get("endpoint_type", "lmstudio")
CONTEXT_LENGTH = _settings.get("context_length", DEFAULT_CONTEXT_LENGTH)
GPU_LAYERS = _settings.get("gpu_layers", DEFAULT_GPU_LAYERS)
CPU_THREADS = _settings.get("cpu_threads", DEFAULT_CPU_THREADS)


# ============== Tool Definitions ==============
# These define the functions the LLM can call to extract and categorize garden data

GARDEN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_plant",
            "description": "Add a new plant to the garden. Use when the user mentions planting something new or adding a plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the plant (e.g., Tomato, Basil, Rose)"
                    },
                    "variety": {
                        "type": "string",
                        "description": "The specific variety of the plant (e.g., Cherry, Roma, Beefsteak for tomatoes)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Where the plant is located (e.g., raised bed 1, pot, greenhouse, front yard)"
                    },
                    "date_planted": {
                        "type": "string",
                        "description": "The date when the plant was planted in ISO format (YYYY-MM-DD)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any additional notes about the plant"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_watering",
            "description": "Log a watering event for a plant. Use when user mentions watering plants.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "The name of the plant that was watered"
                    },
                    "amount_ml": {
                        "type": "number",
                        "description": "Amount of water in milliliters"
                    },
                    "method": {
                        "type": "string",
                        "description": "Watering method (compost tea, spray, soak, hose, watering can)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of watering in ISO format (YYYY-MM-DD)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any additional notes about the watering"
                    }
                },
                "required": ["plant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_fertilization",
            "description": "Log a fertilization event. Use when user mentions fertilizing, feeding plants, or adding nutrients.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "The name of the plant that was fertilized"
                    },
                    "fertilizer_type": {
                        "type": "string",
                        "description": "Type of fertilizer used (e.g., compost tea, fish emulsion, 10-10-10)"
                    },
                    "amount": {
                        "type": "string",
                        "description": "Amount applied (e.g., 1 cup, 2 tablespoons)"
                    },
                    "npk_ratio": {
                        "type": "string",
                        "description": "NPK ratio if known (e.g., 10-10-10)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of fertilization in ISO format (YYYY-MM-DD)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any additional notes"
                    }
                },
                "required": ["plant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_harvest",
            "description": "Log a harvest event. Use when user mentions picking, harvesting, or collecting produce.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "The name of the plant that was harvested"
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Amount harvested"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit of measurement (kg, lbs, pieces, bunches, cups)"
                    },
                    "quality_rating": {
                        "type": "integer",
                        "description": "Quality rating from 1-10"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of harvest in ISO format (YYYY-MM-DD)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any additional notes about the harvest"
                    }
                },
                "required": ["plant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_growth",
            "description": "Log growth measurements for a plant. Use when user mentions height, size, leaf count, or general plant health.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "The name of the plant"
                    },
                    "height_cm": {
                        "type": "number",
                        "description": "Height of the plant in centimeters"
                    },
                    "width_cm": {
                        "type": "number",
                        "description": "Width/spread of the plant in centimeters"
                    },
                    "leaf_count": {
                        "type": "integer",
                        "description": "Number of leaves"
                    },
                    "health_rating": {
                        "type": "integer",
                        "description": "Health rating from 1-10 (10 being excellent)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of measurement in ISO format (YYYY-MM-DD)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any observations about the plant's growth"
                    }
                },
                "required": ["plant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "report_pest_issue",
            "description": "Report a pest or disease issue. Use when user mentions bugs, insects, disease, fungus, or plant problems.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "The name of the affected plant"
                    },
                    "pest_type": {
                        "type": "string",
                        "description": "Type of pest or disease (e.g., aphids, slugs, powdery mildew, blight)"
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["mild", "moderate", "severe"],
                        "description": "Severity of the issue"
                    },
                    "treatment": {
                        "type": "string",
                        "description": "Treatment applied or planned"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date issue was identified in ISO format (YYYY-MM-DD)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional observations about the issue"
                    }
                },
                "required": ["plant_name", "pest_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a garden task or reminder. Use when user mentions needing to do something, planning to do something, or setting a reminder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short title for the task"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the task"
                    },
                    "task_type": {
                        "type": "string",
                        "enum": ["watering", "fertilizing", "pruning", "harvesting", "planting", "pest_control", "maintenance", "other"],
                        "description": "Type of garden task"
                    },
                    "plant_name": {
                        "type": "string",
                        "description": "The plant this task relates to (if applicable)"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "When the task should be done in ISO format (YYYY-MM-DD)"
                    },
                    "recurring": {
                        "type": "boolean",
                        "description": "Whether this task repeats"
                    },
                    "recurrence_interval": {
                        "type": "integer",
                        "description": "Days between recurrence if recurring"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Priority level of the task"
                    }
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_weather",
            "description": "Log weather conditions. Use when user mentions weather, temperature, rain, or climate conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature_high": {
                        "type": "number",
                        "description": "High temperature in Celsius"
                    },
                    "temperature_low": {
                        "type": "number",
                        "description": "Low temperature in Celsius"
                    },
                    "humidity": {
                        "type": "number",
                        "description": "Humidity percentage"
                    },
                    "rainfall_mm": {
                        "type": "number",
                        "description": "Rainfall in millimeters"
                    },
                    "conditions": {
                        "type": "string",
                        "description": "Weather conditions (sunny, cloudy, rainy, stormy, etc.)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of weather observation in ISO format (YYYY-MM-DD)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional weather notes"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_plant_status",
            "description": "Update the status of an existing plant. Use when user mentions a plant died, was removed, or was harvested completely.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "The name of the plant to update"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "harvested", "removed", "dormant"],
                        "description": "New status of the plant"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notes about the status change"
                    }
                },
                "required": ["plant_name", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_general_note",
            "description": "Add a general garden note that doesn't fit other categories. Use for observations, ideas, or general comments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The note content"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category for the note (observation, idea, reminder, other)"
                    }
                },
                "required": ["content"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are a smart garden assistant that helps extract structured data from natural language notes about gardening activities.

Your job is to:
1. Carefully read the user's note about their garden
2. Identify ALL relevant plants, garden activities, observations, and data mentioned
3. Call the appropriate function(s) to log each piece of information to the corrosponding plant. Check if the plant exists in the garden first before making new plant entry. 
4. Extract as much detail as possible from the text

Important guidelines:
- If today's date is mentioned as "today", use the current date provided
- Convert measurements to metric when possible (cm, ml)
- If multiple plants or activities are mentioned, make separate function calls for each
- Infer reasonable values when the user is vague (e.g., "watered a bit" = small amount)
- Always extract dates when mentioned, even relative ones like "yesterday" or "last week"
- For health descriptions like "looking great" = 8-10, "not doing well" = 3-5, "dying" = 1-2

Current date: {current_date}

Available plants in the garden (for reference when logging activities):
{plant_list}

Extract all relevant information and make the appropriate function calls."""


class LLMService:
    def __init__(self, base_url: str = None, model: str = None, api_key: str = None, endpoint_type: str = None, context_length: int = None, 
                 gpu_layers: int = None, cpu_threads: int = None):
        # Always load fresh settings
        settings = load_llm_settings()
        self.base_url = base_url or settings.get("url", DEFAULT_LMSTUDIO_URL)
        self.model = model or settings.get("model", DEFAULT_MODEL_NAME)
        self.api_key = api_key if api_key is not None else settings.get("api_key", "")
        self.endpoint_type = endpoint_type if endpoint_type is not None else settings.get("endpoint_type", "lmstudio")
        self.context_length = context_length if context_length is not None else settings.get("context_length", DEFAULT_CONTEXT_LENGTH)
        self.gpu_layers = gpu_layers if gpu_layers is not None else settings.get("gpu_layers", DEFAULT_GPU_LAYERS)
        self.cpu_threads = cpu_threads if cpu_threads is not None else settings.get("cpu_threads", DEFAULT_CPU_THREADS)
        llm_logger.info(f"LLMService initialized - URL: {self.base_url}, Model: {self.model}, Type: {self.endpoint_type}, Context: {self.context_length}")
    
    def reload_settings(self):
        """Reload settings from file."""
        settings = load_llm_settings()
        self.base_url = settings.get("url", DEFAULT_LMSTUDIO_URL)
        self.model = settings.get("model", DEFAULT_MODEL_NAME)
        self.api_key = settings.get("api_key", "")
        self.endpoint_type = settings.get("endpoint_type", "lmstudio")
        self.context_length = settings.get("context_length", DEFAULT_CONTEXT_LENGTH)
        self.gpu_layers = settings.get("gpu_layers", DEFAULT_GPU_LAYERS)
        self.cpu_threads = settings.get("cpu_threads", DEFAULT_CPU_THREADS)
        llm_logger.info(f"Settings reloaded - URL: {self.base_url}, Model: {self.model}, Type: {self.endpoint_type}")
    
    def extract_garden_data(self, note_text: str, existing_plants: List[str] = None) -> Dict[str, Any]:
        """
        Extract structured garden data from a natural language note.
        
        Args:
            note_text: The user's note about their garden
            existing_plants: List of plant names already in the garden
            
        Returns:
            Dictionary containing extracted data and function calls
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        plant_list = ", ".join(existing_plants) if existing_plants else "No plants registered yet"
        
        system_message = SYSTEM_PROMPT.format(
            current_date=current_date,
            plant_list=plant_list
        )
        
        request_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": note_text}
            ],
            "tools": GARDEN_TOOLS,
            "tool_choice": "auto",
            "temperature": 0.3
        }
        
        # Add vLLM vs LMStudio specific parameters
        if self.endpoint_type != "vllm":
            request_payload["max_tokens"] = 2000
            request_payload["n_ctx"] = self.context_length
            request_payload["n_gpu_layers"] = self.gpu_layers
            request_payload["n_threads"] = self.cpu_threads
        else:
            # vLLM requires max_tokens >= 1 if provided, but it's often better to let it use the model default
            # We explicitly don't pass -1 or LMStudio-specific threading parameters
            pass
        
        llm_logger.debug(f"=== LLM REQUEST ===")
        llm_logger.debug(f"URL: {self.base_url}")
        llm_logger.debug(f"Model: {self.model}")
        llm_logger.debug(f"Note text: {note_text}")
        llm_logger.debug(f"Existing plants: {existing_plants}")
        llm_logger.debug(f"Request payload (without tools): {json.dumps({k:v for k,v in request_payload.items() if k != 'tools'}, indent=2)}")
        
        try:
            llm_logger.info(f"Sending request to {self.base_url}...")
            
            headers = {"Content-Type": "application/json", **PRISM_ATTRIBUTION_HEADERS}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            response = requests.post(
                self.base_url,
                headers=headers,
                json=request_payload,
                timeout=60
            )
            
            llm_logger.debug(f"=== LLM RESPONSE ===")
            llm_logger.debug(f"Status code: {response.status_code}")
            llm_logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Log raw response text before parsing
            raw_response = response.text
            llm_logger.debug(f"Raw response (first 2000 chars): {raw_response[:2000]}")
            
            response.raise_for_status()
            result = response.json()
            
            llm_logger.debug(f"Parsed JSON response: {json.dumps(result, indent=2)[:3000]}")
            llm_logger.info(f"Request successful, processing response...")
            
            return self._process_response(result, note_text)
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error to {self.base_url}: {str(e)}"
            llm_logger.error(error_msg)
            return {
                "success": False,
                "error": f"Could not connect to LMStudio at {self.base_url}. Make sure it's running.",
                "error_details": str(e),
                "raw_note": note_text,
                "extracted_actions": []
            }
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout connecting to {self.base_url}: {str(e)}"
            llm_logger.error(error_msg)
            return {
                "success": False,
                "error": "LMStudio request timed out after 60 seconds",
                "error_details": str(e),
                "raw_note": note_text,
                "extracted_actions": []
            }
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error from {self.base_url}: {str(e)}"
            llm_logger.error(error_msg)
            llm_logger.error(f"Response body: {response.text[:2000] if response else 'No response'}")
            return {
                "success": False,
                "error": f"HTTP error: {response.status_code} - {response.reason}",
                "error_details": response.text[:500] if response else str(e),
                "raw_note": note_text,
                "extracted_actions": []
            }
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error: {str(e)}"
            llm_logger.error(error_msg)
            llm_logger.error(f"Raw response that failed to parse: {raw_response[:1000]}")
            return {
                "success": False,
                "error": "Failed to parse LLM response as JSON",
                "error_details": str(e),
                "raw_note": note_text,
                "extracted_actions": []
            }
        except Exception as e:
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            llm_logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "raw_note": note_text,
                "extracted_actions": []
            }
    
    def _process_response(self, response: Dict, original_note: str) -> Dict[str, Any]:
        """Process the LLM response and extract tool calls."""
        extracted_actions = []
        
        llm_logger.debug(f"=== PROCESSING RESPONSE ===")
        
        try:
            choices = response.get("choices", [])
            llm_logger.debug(f"Number of choices: {len(choices)}")
            
            if not choices:
                llm_logger.warning("No choices in response")
                return {
                    "success": False,
                    "error": "LLM returned no choices in response",
                    "raw_note": original_note,
                    "extracted_actions": [],
                    "raw_response": response
                }
            
            message = choices[0].get("message", {})
            llm_logger.debug(f"Message keys: {message.keys()}")
            
            tool_calls = message.get("tool_calls", [])
            llm_logger.debug(f"Number of tool calls: {len(tool_calls)}")
            
            # Check if the model doesn't support tool calling
            finish_reason = choices[0].get("finish_reason", "")
            llm_logger.debug(f"Finish reason: {finish_reason}")
            
            if not tool_calls and message.get("content"):
                llm_logger.warning(f"No tool calls found. Model may not support function calling.")
                llm_logger.warning(f"Content returned: {message.get('content', '')[:500]}")
                return {
                    "success": False,
                    "error": "Model did not return any tool calls. It may not support function calling.",
                    "assistant_message": message.get("content", ""),
                    "raw_note": original_note,
                    "extracted_actions": [],
                    "hint": "Try using a model that supports function/tool calling like granite, mistral, or llama with function calling support."
                }
            
            for i, tool_call in enumerate(tool_calls):
                llm_logger.debug(f"Processing tool call {i}: {tool_call}")
                function_info = tool_call.get("function", {})
                function_name = function_info.get("name")
                
                # Parse the arguments - handle both string and dict
                arguments = function_info.get("arguments", "{}")
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError as e:
                        llm_logger.error(f"Failed to parse arguments for {function_name}: {e}")
                        llm_logger.error(f"Raw arguments: {arguments}")
                        arguments = {}
                
                llm_logger.info(f"Extracted action: {function_name} with params: {arguments}")
                extracted_actions.append({
                    "action": function_name,
                    "parameters": arguments,
                    "tool_call_id": tool_call.get("id")
                })
            
            # Also get any text response
            assistant_message = message.get("content", "")
            
            llm_logger.info(f"Successfully extracted {len(extracted_actions)} actions")
            
            return {
                "success": True,
                "raw_note": original_note,
                "extracted_actions": extracted_actions,
                "assistant_message": assistant_message,
                "action_count": len(extracted_actions)
            }
            
        except Exception as e:
            llm_logger.error(f"Error processing response: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Error processing response: {str(e)}",
                "raw_note": original_note,
                "extracted_actions": []
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test if LMStudio is running and accessible with detailed diagnostics."""
        llm_logger.info(f"=== CONNECTION TEST ===")
        llm_logger.info(f"Testing connection to: {self.base_url}")
        llm_logger.info(f"Using model: {self.model}")
        
        result = {
            "connected": False,
            "url": self.base_url,
            "model": self.model,
            "message": ""
        }
        
        try:
            # First, try a simple request
            llm_logger.debug("Sending test request...")
            
            headers = {"Content-Type": "application/json", **PRISM_ATTRIBUTION_HEADERS}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            response = requests.post(
                self.base_url,
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": "Hello, respond with just 'OK' if you can hear me."}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 10
                },
                timeout=15
            )
            
            llm_logger.debug(f"Response status: {response.status_code}")
            llm_logger.debug(f"Response body: {response.text[:500]}")
            
            response.raise_for_status()
            response_data = response.json()
            
            # Check if we got a valid response
            if response_data.get("choices"):
                content = response_data["choices"][0].get("message", {}).get("content", "")
                result["connected"] = True
                result["message"] = "LMStudio is connected and responding"
                result["model_response"] = content[:100]
                result["supports_tools"] = "Unknown - use 'Test Tool Calling' to verify"
                llm_logger.info(f"Connection successful! Model response: {content[:100]}")
            else:
                result["message"] = "Connected but got unexpected response format"
                result["raw_response"] = str(response_data)[:200]
                llm_logger.warning(f"Unexpected response format: {response_data}")
                
        except requests.exceptions.ConnectionError as e:
            result["message"] = f"Cannot connect to LMStudio at {self.base_url}. Make sure it's running."
            result["error_type"] = "ConnectionError"
            result["error_details"] = str(e)
            llm_logger.error(f"Connection error: {e}")
            
        except requests.exceptions.Timeout as e:
            result["message"] = "Connection timed out. LMStudio may be starting up or overloaded."
            result["error_type"] = "Timeout"
            result["error_details"] = str(e)
            llm_logger.error(f"Timeout: {e}")
            
        except requests.exceptions.HTTPError as e:
            result["message"] = f"HTTP error: {response.status_code}"
            result["error_type"] = "HTTPError"
            result["error_details"] = response.text[:300] if response else str(e)
            llm_logger.error(f"HTTP error: {e}")
            
        except Exception as e:
            result["message"] = f"Unexpected error: {str(e)}"
            result["error_type"] = type(e).__name__
            result["error_details"] = str(e)
            llm_logger.error(f"Unexpected error: {e}", exc_info=True)
        
        return result
    
    def test_tool_calling(self) -> Dict[str, Any]:
        """Test if the model supports tool/function calling."""
        llm_logger.info(f"=== TOOL CALLING TEST ===")
        
        simple_tool = [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"}
                    },
                    "required": ["location"]
                }
            }
        }]
        
        try:
            headers = {"Content-Type": "application/json", **PRISM_ATTRIBUTION_HEADERS}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            response = requests.post(
                self.base_url,
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": "What's the weather in New York?"}
                    ],
                    "tools": simple_tool,
                    "tool_choice": "auto",
                    "temperature": 0.1
                },
                timeout=15
            )
            
            llm_logger.debug(f"Tool test response: {response.text[:1000]}")
            response.raise_for_status()
            data = response.json()
            
            message = data.get("choices", [{}])[0].get("message", {})
            tool_calls = message.get("tool_calls", [])
            
            if tool_calls:
                llm_logger.info(f"Tool calling supported! Got {len(tool_calls)} tool calls")
                return {
                    "supports_tools": True,
                    "message": f"Model supports tool calling. Received {len(tool_calls)} tool call(s).",
                    "tool_calls": tool_calls
                }
            else:
                content = message.get("content", "")
                llm_logger.warning(f"No tool calls returned. Content: {content[:200]}")
                return {
                    "supports_tools": False,
                    "message": "Model did not use tool calling. It may not support this feature.",
                    "model_response": content[:200],
                    "hint": "Try a model like granite, mistral-instruct, or llama with function calling support."
                }
                
        except Exception as e:
            llm_logger.error(f"Tool calling test failed: {e}", exc_info=True)
            return {
                "supports_tools": False,
                "message": f"Tool calling test failed: {str(e)}",
                "error": str(e)
            }


# Flask routes for LLM service
def register_llm_routes(app, db):
    """Register LLM-related routes with the Flask app."""
    from backend.app import Plant, GardenNote, Watering, Fertilization, Harvest, GrowthLog, PestIssue, Task, WeatherLog
    
    llm_service = LLMService()
    
    @app.route('/api/llm/status', methods=['GET'])
    def llm_status():
        """Check LLM connection status."""
        # Reload settings to get latest config
        llm_service.reload_settings()
        return jsonify(llm_service.test_connection())
    
    @app.route('/api/llm/test-tools', methods=['GET'])
    def test_tools():
        """Test if the model supports tool calling."""
        llm_service.reload_settings()
        return jsonify(llm_service.test_tool_calling())
    
    @app.route('/api/llm/settings', methods=['GET'])
    def get_llm_settings():
        """Get current LLM settings."""
        settings = load_llm_settings()
        return jsonify({
            "url": settings.get("url", DEFAULT_LMSTUDIO_URL),
            "model": settings.get("model", DEFAULT_MODEL_NAME),
            "defaults": {
                "url": DEFAULT_LMSTUDIO_URL,
                "model": DEFAULT_MODEL_NAME
            }
        })
    
    @app.route('/api/llm/settings', methods=['POST'])
    def update_llm_settings():
        """Update LLM settings."""
        data = request.json
        url = data.get('url', DEFAULT_LMSTUDIO_URL)
        model = data.get('model', DEFAULT_MODEL_NAME)
        
        if save_llm_settings(url, model):
            llm_service.reload_settings()
            return jsonify({
                "success": True,
                "message": "Settings saved successfully",
                "url": url,
                "model": model
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to save settings"
            }), 500
    
    @app.route('/api/llm/logs', methods=['GET'])
    def get_llm_logs():
        """Get recent LLM debug logs."""
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    # Return last 100 lines
                    return jsonify({
                        "logs": lines[-100:],
                        "log_file": log_file
                    })
            return jsonify({"logs": [], "message": "No log file found"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/llm/process-note', methods=['POST'])
    def process_note():
        """Process a natural language note and extract garden data."""
        try:
            # Reload settings before processing
            llm_service.reload_settings()
            
            data = request.json
            note_text = data.get('note', '')
            
            if not note_text:
                return jsonify({"error": "No note text provided"}), 400
            
            # Get existing plant names for context
            plants = Plant.query.filter_by(status='active').all()
            plant_names = [p.name for p in plants]
            
            # Extract data from note
            result = llm_service.extract_garden_data(note_text, plant_names)
            
            # Save the note
            note = GardenNote(
                raw_text=note_text,
                processed=result.get('success', False),
                extracted_data=json.dumps(result.get('extracted_actions', []))
            )
            db.session.add(note)
            db.session.commit()
            
            result['note_id'] = note.id
            return jsonify(result)
        except Exception as e:
            llm_logger.error(f"Error in process_note: {type(e).__name__}: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"Server error: {str(e)}",
                "error_type": type(e).__name__,
                "hint": "Check if LMStudio is running and the model is loaded. See llm_debug.log for details."
            }), 500
    
    @app.route('/api/llm/apply-actions', methods=['POST'])
    def apply_actions():
        """Apply extracted actions to the database."""
        data = request.json
        actions = data.get('actions', [])
        results = []
        
        for action in actions:
            action_type = action.get('action')
            params = action.get('parameters', {})
            
            try:
                result = _apply_single_action(action_type, params, db, Plant, Watering, 
                                            Fertilization, Harvest, GrowthLog, PestIssue, 
                                            Task, WeatherLog)
                results.append(result)
            except Exception as e:
                results.append({
                    "action": action_type,
                    "success": False,
                    "error": str(e)
                })
        
        db.session.commit()
        return jsonify({"results": results})


def _apply_single_action(action_type: str, params: Dict, db, Plant, Watering, 
                         Fertilization, Harvest, GrowthLog, PestIssue, Task, WeatherLog) -> Dict:
    """Apply a single extracted action to the database."""
    
    def find_or_create_plant(name: str) -> Optional[Plant]:
        """Find existing plant or create new one."""
        plant = Plant.query.filter(Plant.name.ilike(f"%{name}%")).first()
        if not plant:
            plant = Plant(name=name, status='active')
            db.session.add(plant)
            db.session.flush()
        return plant
    
    def parse_date(date_str: str) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return datetime.utcnow()
        try:
            return datetime.fromisoformat(date_str)
        except:
            return datetime.utcnow()
    
    if action_type == "add_plant":
        plant = Plant(
            name=params.get('name'),
            variety=params.get('variety'),
            location=params.get('location'),
            date_planted=parse_date(params.get('date_planted')),
            notes=params.get('notes'),
            status='active'
        )
        db.session.add(plant)
        return {"action": action_type, "success": True, "message": f"Added plant: {params.get('name')}"}
    
    elif action_type == "log_watering":
        plant = find_or_create_plant(params.get('plant_name'))
        watering = Watering(
            plant_id=plant.id,
            date=parse_date(params.get('date')),
            amount_ml=params.get('amount_ml'),
            method=params.get('method'),
            notes=params.get('notes')
        )
        db.session.add(watering)
        return {"action": action_type, "success": True, "message": f"Logged watering for: {params.get('plant_name')}"}
    
    elif action_type == "log_fertilization":
        plant = find_or_create_plant(params.get('plant_name'))
        fertilization = Fertilization(
            plant_id=plant.id,
            date=parse_date(params.get('date')),
            fertilizer_type=params.get('fertilizer_type'),
            amount=params.get('amount'),
            npk_ratio=params.get('npk_ratio'),
            notes=params.get('notes')
        )
        db.session.add(fertilization)
        return {"action": action_type, "success": True, "message": f"Logged fertilization for: {params.get('plant_name')}"}
    
    elif action_type == "log_harvest":
        plant = find_or_create_plant(params.get('plant_name'))
        harvest = Harvest(
            plant_id=plant.id,
            date=parse_date(params.get('date')),
            quantity=params.get('quantity'),
            unit=params.get('unit'),
            quality_rating=params.get('quality_rating'),
            notes=params.get('notes')
        )
        db.session.add(harvest)
        return {"action": action_type, "success": True, "message": f"Logged harvest for: {params.get('plant_name')}"}
    
    elif action_type == "log_growth":
        plant = find_or_create_plant(params.get('plant_name'))
        growth = GrowthLog(
            plant_id=plant.id,
            date=parse_date(params.get('date')),
            height_cm=params.get('height_cm'),
            width_cm=params.get('width_cm'),
            leaf_count=params.get('leaf_count'),
            health_rating=params.get('health_rating'),
            notes=params.get('notes')
        )
        db.session.add(growth)
        return {"action": action_type, "success": True, "message": f"Logged growth for: {params.get('plant_name')}"}
    
    elif action_type == "report_pest_issue":
        plant = find_or_create_plant(params.get('plant_name'))
        pest = PestIssue(
            plant_id=plant.id,
            date_identified=parse_date(params.get('date')),
            pest_type=params.get('pest_type'),
            severity=params.get('severity', 'moderate'),
            treatment=params.get('treatment'),
            notes=params.get('notes')
        )
        db.session.add(pest)
        return {"action": action_type, "success": True, "message": f"Reported pest issue for: {params.get('plant_name')}"}
    
    elif action_type == "create_task":
        plant = None
        if params.get('plant_name'):
            plant = Plant.query.filter(Plant.name.ilike(f"%{params.get('plant_name')}%")).first()
        
        task = Task(
            title=params.get('title'),
            description=params.get('description'),
            task_type=params.get('task_type', 'other'),
            plant_id=plant.id if plant else None,
            due_date=parse_date(params.get('due_date')),
            recurring=params.get('recurring', False),
            recurrence_interval=params.get('recurrence_interval'),
            priority=params.get('priority', 'medium')
        )
        db.session.add(task)
        return {"action": action_type, "success": True, "message": f"Created task: {params.get('title')}"}
    
    elif action_type == "log_weather":
        weather = WeatherLog(
            date=parse_date(params.get('date')),
            temperature_high=params.get('temperature_high'),
            temperature_low=params.get('temperature_low'),
            humidity=params.get('humidity'),
            rainfall_mm=params.get('rainfall_mm'),
            conditions=params.get('conditions'),
            notes=params.get('notes')
        )
        db.session.add(weather)
        return {"action": action_type, "success": True, "message": "Logged weather conditions"}
    
    elif action_type == "update_plant_status":
        plant = Plant.query.filter(Plant.name.ilike(f"%{params.get('plant_name')}%")).first()
        if plant:
            plant.status = params.get('status', 'active')
            if params.get('notes'):
                plant.notes = (plant.notes or '') + '\n' + params.get('notes')
            return {"action": action_type, "success": True, "message": f"Updated status for: {params.get('plant_name')}"}
        return {"action": action_type, "success": False, "message": f"Plant not found: {params.get('plant_name')}"}
    
    elif action_type == "add_general_note":
        return {"action": action_type, "success": True, "message": "Note saved", "content": params.get('content')}
    
    else:
        return {"action": action_type, "success": False, "message": f"Unknown action type: {action_type}"}


if __name__ == "__main__":
    # Test the service
    service = LLMService()
    print("Testing LMStudio connection...")
    print(service.test_connection())
    
    # Test extraction
    test_note = "Today I planted 3 cherry tomato seedlings in the raised bed. Also watered all my basil plants and noticed some aphids on the pepper plant."
    print("\nTesting extraction with note:")
    print(test_note)
    print("\nResult:")
    print(json.dumps(service.extract_garden_data(test_note, ["Basil", "Pepper"]), indent=2))
