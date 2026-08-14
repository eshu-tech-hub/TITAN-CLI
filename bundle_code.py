import os

def bundle_python_files(output_filename="all_project_code.txt"):
    current_dir = os.getcwd()
    excluded_dirs = {".venv", "__pycache__", ".git", ".pytest_cache", "build", "dist"}
    
    with open(output_filename, "w", encoding="utf-8") as outfile:
        for root, dirs, files in os.walk(current_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            
            for file in files:
                if file.endswith(".py") and file != "bundle_code.py":
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, current_dir)
                    
                    outfile.write(f"\n{'='*80}\n")
                    outfile.write(f"FILE: {relative_path}\n")
                    outfile.write(f"{'='*80}\n\n")
                    
                    try:
                        with open(file_path, "r", encoding="utf-8") as infile:
                            outfile.write(infile.read())
                        outfile.write("\n")
                    except Exception as e:
                        outfile.write(f"# Error reading file: {e}\n")

    print(f"Successfully bundled all .py files into: {output_filename}")

if __name__ == "__main__":
    bundle_python_files()