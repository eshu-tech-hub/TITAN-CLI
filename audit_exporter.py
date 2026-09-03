import json
import os


def export_project_to_json(output_filename="titan_code_dump.json"):
    project_data = {}
    
    # Directories to completely ignore to keep the file size manageable
    exclude_dirs = {
        ".venv", ".git", "__pycache__", ".pytest_cache", 
        ".mypy_cache", ".ruff_cache", "logs", "data", "reports"
    }
    
    # Only grab relevant source code and config files
    valid_extensions = {".py", ".yaml", ".yml", ".toml"}

    for root, dirs, files in os.walk("."):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_extensions and file != output_filename and file != "export_code.py":
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, ".")
                
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        project_data[rel_path] = f.read()
                except Exception as e:
                    project_data[rel_path] = f"<ERROR READING FILE: {e}>"

    # Write everything to a structured JSON file
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=2)

    print(f"Success! {len(project_data)} files exported to {output_filename}")

if __name__ == "__main__":
    export_project_to_json()