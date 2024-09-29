import json
import os

# Define the path to the settings JSON file
SETTINGS_FILE = 'settings.json'

# This dictionary will hold the settings in memory
settings = {}

def load_settings():
    """Load settings from the JSON file."""
    global settings
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
    else:
        # If the file doesn't exist, initialize with default settings
        settings = get_default_settings()
        _save_settings()

def get_default_settings():
    """Return default settings."""
    return {
    'NODE_ID': os.getenv('NODE_ID', '127.0.0.1:5000'),
    'LAST_EXECUTION_FILE': 'last_execution.txt',
    'INDEX_FILES_TIME': 1,
    'PEER_DISCOVER_INTERVAL': 1,
    'DIRECTORY': '/the/directory/to/be/shared',
    'URL': 'https://raw.githubusercontent.com/username/repository/branch/path/to/file.json',
    'HEARTBEAT_INTERVAL': 10,
    'known_nodes': set(os.getenv('KNOWN_NODES', '').split(', ')),
}

def _save_settings():
    """Save the current settings to the JSON file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def get_setting(key, default=None):
    """Retrieve a setting value by key."""
    return settings.get(key, default)

def set_setting(key, value):
    """Set a setting value and save the updated settings to the file."""
    settings[key] = value
    _save_settings()

def return_all():
    return settings

# Automatically load settings when the module is imported
load_settings()

