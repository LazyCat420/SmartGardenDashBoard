
import os
import json
import sys
import shutil

# Add backend directory to path so we can import main
sys.path.append(os.path.join(os.getcwd(), 'backend'))

def run_test():
    settings_path = os.path.join('backend', 'llm_settings.json')
    backup_path = settings_path + '.bak'
    result_file = 'verification_result.txt'
    
    # Backup existing settings
    if os.path.exists(settings_path):
        shutil.copy2(settings_path, backup_path)
    
    try:
        # Create test settings
        test_settings = {
            "url": "http://test-url:1234/v1/chat/completions",
            "model": "test-model-v1"
        }
        with open(settings_path, 'w') as f:
            json.dump(test_settings, f)
            
        # Import main_md to trigger startup logic
        import main_md as main
        
        with open(result_file, 'w') as f:
            f.write(f"Loaded URL: {main.LMSTUDIO_URL}\n")
            f.write(f"Loaded Model: {main.MODEL_NAME}\n")
            
            if main.LMSTUDIO_URL == test_settings["url"] and main.MODEL_NAME == test_settings["model"]:
                f.write("Result: SUCCESS\n")
            else:
                f.write("Result: FAILURE\n")
                f.write(f"Expected URL: {test_settings['url']}\n")
                f.write(f"Expected Model: {test_settings['model']}\n")
            
    except Exception as e:
        with open(result_file, 'w') as f:
            f.write(f"Error: {e}\n")
    finally:
        # Restore backup
        if os.path.exists(backup_path):
            shutil.move(backup_path, settings_path)
        
        # Cleanup extra files if needed, but we keep result_file to read it.

if __name__ == "__main__":
    run_test()
