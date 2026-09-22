import os
import json
from datetime import datetime

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)

STATE_FILE = os.path.join(PROJECT_ROOT, "data/files/files_state.json")
RAW_DIR = os.path.join(PROJECT_ROOT, "data/files/raw_files")
MD_DIR = os.path.join(PROJECT_ROOT, "data/files/md_files")


def get_last_modified(file_path):
    timestamp = os.path.getmtime(file_path)
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def load_state():
    if not os.path.exists(STATE_FILE):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)

        return []

    

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_file_changes():
    state = load_state()

    current_files = sorted( 
        file for file in os.listdir(RAW_DIR) 
        if os.path.isfile(os.path.join(RAW_DIR, file)) 
    )



    state_files = { item["raw_file_name"]: item for item in state }
    

    # for file in current_files:
    #     actual_time = get_last_modified(os.path.join(RAW_DIR, file))
    #     json_time = state_files[file]["last_modified_date"]

    #     print(file)
    #     print("  Actual:", actual_time)
    #     print("  JSON:  ", json_time)

    new_files = [
        file for file in current_files
        if file not in state_files
    ]

    deleted_files = [
        file for file in state_files
        if file not in current_files
    ]

    updated_files = [
        file for file in current_files
        if file in state_files
        and get_last_modified(os.path.join(RAW_DIR, file))
        != state_files[file]["raw_file_last_modified_date"]
    ]

    return new_files, deleted_files, updated_files


