"""
Configuration file for the TIPQIC RAG Chatbot frontend.
Update this file when deploying to different environments.
"""

import os
import json
from pathlib import Path

# Default configuration
DEFAULT_CONFIG = {
    "api_host": "localhost",
    "api_port": 8000,
    "frontend_port": 8501
}

CONFIG_FILE = Path(__file__).parent / "app_config.json"

def load_config():
    """Load configuration from file or use defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return {**DEFAULT_CONFIG, **config}
        except (json.JSONDecodeError, IOError):
            pass
    
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False

def update_api_config(host, port):
    """Update API configuration and save to file."""
    config = load_config()
    config["api_host"] = host
    config["api_port"] = port
    return save_config(config)

def get_api_base_url():
    """Get the API base URL from configuration."""
    config = load_config()
    return f"http://{config['api_host']}:{config['api_port']}"

def get_frontend_port():
    """Get the frontend port from configuration."""
    config = load_config()
    return config["frontend_port"]
