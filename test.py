import requests
import json
import os
from email.utils import parsedate_to_datetime
from datetime import timezone
from zoneinfo import ZoneInfo

URL = "https://github.com/dgtlmoon/changedetection.io"
STATE_FILE = "page_state.json"

IST = ZoneInfo("Asia/Kolkata")


def convert_to_ist(http_date):
    if not http_date:
        return None

    # Parse HTTP date, which is normally GMT/UTC
    dt = parsedate_to_datetime(http_date)

    # Convert to IST
    dt_ist = dt.astimezone(IST)

    return dt_ist.strftime("%Y-%m-%d %H:%M:%S %Z")


def check_page(url):
    headers = {
        "User-Agent": "RAG-Page-Validator/1.0"
    }

    old_state = {}

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            old_state = json.load(f)

        if old_state.get("last_modified"):
            headers["If-Modified-Since"] = old_state["last_modified"]

        if old_state.get("etag"):
            headers["If-None-Match"] = old_state["etag"]

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    last_modified = response.headers.get("Last-Modified")
    etag = response.headers.get("ETag")

    print("HTTP status:", response.status_code)
    print("ETag:", etag)
    print("Last-Modified (server):", last_modified)
    print("Last-Modified (IST):", convert_to_ist(last_modified))

    if response.status_code == 304:
        print("\n✅ PAGE NOT CHANGED")
        return False

    if response.status_code == 200:

        new_state = {
            "url": url,
            "etag": etag,
            "last_modified": last_modified
        }

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(new_state, f, indent=4)

        if old_state:
            print("\n⚠️ PAGE CHANGED")
        else:
            print("\n🆕 FIRST CHECK - state saved")

        return True

    print(f"\n❌ Unexpected HTTP status: {response.status_code}")
    return None


check_page(URL)