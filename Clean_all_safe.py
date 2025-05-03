import os
import shutil

# Configuration: Set to True only if you're sure
DELETE_ENV = False
DELETE_LOGS = True
DELETE_DB = False

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def delete_pycache_and_pyc():
    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        for dirname in dirnames:
            if dirname == '__pycache__':
                full_path = os.path.join(dirpath, dirname)
                shutil.rmtree(full_path)
                print(f"🧹 Removed directory: {full_path}")

        for filename in filenames:
            if filename.endswith('.pyc'):
                full_path = os.path.join(dirpath, filename)
                os.remove(full_path)
                print(f"🧽 Removed file: {full_path}")

def delete_logs_and_env():
    for filename in os.listdir(ROOT_DIR):
        full_path = os.path.join(ROOT_DIR, filename)
        if DELETE_LOGS and filename.endswith(".log"):
            os.remove(full_path)
            print(f"🗑️ Removed log file: {full_path}")
        if DELETE_ENV and filename == ".env":
            os.remove(full_path)
            print(f"⚠️ Removed .env file: {full_path}")
        if DELETE_DB and filename.endswith(".db"):
            os.remove(full_path)
            print(f"⚠️ Removed DB file: {full_path}")

def main():
    print("==> Starting clean up...")
    delete_pycache_and_pyc()
    delete_logs_and_env()
    print("✅ Cleanup complete!")

if __name__ == "__main__":
    main()