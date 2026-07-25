import os


def generate_targeted_audit_export():
    output_file = "titan_targeted_audit_export.txt"

    exclude_dirs = {
        ".venv",
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "titan_cli.egg-info",
        ".github",
        "logs",
    }

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=== TITAN ARCHITECTURE TREE ===\n\n")

        # 1. Walk and map the directory tree
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            level = root.replace(".", "").count(os.sep)
            indent = " " * 4 * level
            f.write(f"{indent}{os.path.basename(root)}/\n")

            subindent = " " * 4 * (level + 1)
            for file in files:
                if file == output_file:
                    continue
                f.write(f"{subindent}{file}\n")

        f.write("\n\n=== TARGETED FILE INSPECTION ===\n\n")

        # 2. Specific target files requested
        target_files = [
            "titan/portfolio/models.py",
            "titan/portfolio/analytics.py",
            "titan/tui/models.py",
            "titan/tui/layout.py",
            "titan/tui/screens/portfolio.py",
        ]

        for filepath in target_files:
            f.write(f"\n--- FILE: {filepath} ---\n")
            if os.path.exists(filepath):
                try:
                    with open(
                        filepath, "r", encoding="utf-8", errors="ignore"
                    ) as target:
                        f.write(target.read())
                except Exception as e:
                    f.write(f"[Could not read file contents: {e}]\n")
            else:
                f.write("[File not found or not created yet]\n")

    print(f"Targeted audit export complete! Open '{output_file}' to view the results.")


if __name__ == "__main__":
    generate_targeted_audit_export()
