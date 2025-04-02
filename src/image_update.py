import requests
import json
import os
from datetime import datetime

DOCKER_IMAGE = "pdfix/pdf-accessibility-openai"
CONFIG_FILE = "config.json"
LAST_CHECK_FILE = ".local_data.json"

def get_current_version():
    """Read the current version from config.json."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("version", "unknown")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading {CONFIG_FILE}: {e}")
        return "unknown"

def get_latest_docker_version():
    """Fetch the latest available version from Docker Hub."""
    url = f"https://hub.docker.com/v2/repositories/{DOCKER_IMAGE}/tags?page_size=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        tags = response.json().get("results", [])
        if tags:
            return tags[0]["name"]  # Latest tag
    except requests.RequestException as e:
        print(f"Error checking for updates: {e}")
    return None

def last_check_today():
    """Check if the last update check was today by reading last_check.json."""
    if os.path.exists(LAST_CHECK_FILE):
        try:
            with open(LAST_CHECK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                last_date = data.get("last_check", "")
                return last_date == datetime.now().strftime("%Y-%m-%d")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading {LAST_CHECK_FILE}: {e}")
    return False

def update_last_check():
    """Store today's date in last_check.json."""
    try:
        with open(LAST_CHECK_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_check": datetime.now().strftime("%Y-%m-%d")}, f)
    except Exception as e:
        print(f"Error writing {LAST_CHECK_FILE}: {e}")

def check_for_image_updates():
    try:
        if not last_check_today():
            current_version = get_current_version()
            latest_version = get_latest_docker_version()

            if latest_version and latest_version != current_version:
                print(f"🚀 A new Docker image version ({latest_version}) is available! "
                    f"Update with: `docker pull {DOCKER_IMAGE}:{latest_version}`")
                
            update_last_check()
    finally:
        # do not print if check for update fails
        pass
