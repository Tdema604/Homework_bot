import os
import shutil

def clean_file(filepath, backup_folder):
    # Create backup
    backup_path = os.path.join(backup_folder, os.path.basename(filepath))
    shutil.copy(filepath, backup_path)

    # Clean the file
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    clean_lines = [line.encode("ascii", "ignore").decode() for line in lines]
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(clean_lines)

    print(f" Cleaned: {filepath} (Backup saved to: {backup_path})")

def clean_all_py_files(folder):
    backup_folder = os.path.join(folder, "backup")
    os.makedirs(backup_folder, exist_ok=True)

    this_script = os.path.basename(__file__)  # This fixes the variable name

    for filename in os.listdir(folder):
        if filename.endswith(".py") and filename != this_script:
            filepath = os.path.join(folder, filename)
            clean_file(filepath, backup_folder)

if __name__ == "__main__":
    folder = "."  # Current folder
    clean_all_py_files(folder)
    print(" All .py files cleaned with backup.")