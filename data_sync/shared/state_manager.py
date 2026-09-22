import os
import json
from datetime import datetime

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)

def get_last_modified(STATE_FILE):
    file_path = os.path.join(PROJECT_ROOT, STATE_FILE)

    timestamp = os.path.getmtime(file_path)

    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

def load_state(STATE_FILE):
    print("STATE_FILE1:", STATE_FILE)
    STATE_FILE = os.path.join(PROJECT_ROOT, STATE_FILE)
    print("STATE_FILE2:", STATE_FILE)

    if not os.path.exists(STATE_FILE):
        return []

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(STATE_FILE, state):
    STATE_FILE = os.path.join(PROJECT_ROOT, STATE_FILE)

    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)


def add_entry(STATE_FILE, entry):
    STATE_FILE = os.path.join(PROJECT_ROOT, STATE_FILE)

    state = load_state(STATE_FILE)
    state.append(entry)
    save_state(STATE_FILE, state)


def update_entry(STATE_FILE, file_name, updates):
    STATE_FILE = os.path.join(PROJECT_ROOT, STATE_FILE)

    state = load_state(STATE_FILE)

    for entry in state:
        if entry["raw_file_name"] == file_name:
            entry.update(updates)
            break

    save_state(STATE_FILE, state)
    
def delete_entry(STATE_FILE, file_name):
    STATE_FILE = os.path.join(PROJECT_ROOT, STATE_FILE)

    state = load_state(STATE_FILE)

    state = [
        entry for entry in state
        if entry["file_name"] != file_name
    ]

    save_state(STATE_FILE, state)