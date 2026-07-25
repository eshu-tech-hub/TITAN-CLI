import os


def generate_docs():
    root_dir = r"d:\Projects\TITAN-CLI"
    output_file = os.path.join(root_dir, "titan_documentation.md")

    exclude_dirs = {
        ".git",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "logs",
        "titan_cli.egg-info",
    }
    valid_extensions = {".py", ".md", ".json", ".toml"}

    # Avoid writing to the output file if it's already in the directory
    if os.path.exists(output_file):
        os.remove(output_file)

    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write("# TITAN-CLI Project Documentation\n\n")

        for dirpath, dirnames, filenames in os.walk(root_dir):
            # modify dirnames in-place to skip excluded directories
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if (
                    ext in valid_extensions
                    and filename != "titan_documentation.md"
                    and filename != "generate_doc.py"
                ):
                    filepath = os.path.join(dirpath, filename)
                    rel_path = os.path.relpath(filepath, root_dir)

                    try:
                        with open(filepath, "r", encoding="utf-8") as infile:
                            content = infile.read()

                        outfile.write(f"## File: `{rel_path}`\n\n")
                        lang = ext.lstrip(".")
                        if lang == "py":
                            lang = "python"
                        outfile.write(f"```{lang}\n")
                        outfile.write(content)
                        if not content.endswith("\n"):
                            outfile.write("\n")
                        outfile.write("```\n\n")
                    except Exception as e:
                        outfile.write(f"## File: `{rel_path}`\n\n")
                        outfile.write(f"*Error reading file: {e}*\n\n")


if __name__ == "__main__":
    generate_docs()
    print("Documentation generated successfully.")
