import json
import os

def set_environment_variables_from_json(json_path):
    try:
        with open(json_path, 'r') as file:
            variables = json.load(file)
            for key, value in variables.items():
                # Convert boolean values to strings
                if isinstance(value, bool):
                    value = str(value).lower()
                os.environ[key] = str(value)
    except FileNotFoundError:
        print(f"File not found: {json_path}")
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {json_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    json_file_path = 'config/environment_variables-template.json'  # Adjust the path if necessary
    set_environment_variables_from_json(json_file_path)

