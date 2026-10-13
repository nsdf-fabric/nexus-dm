import json
import os
from typing import Dict

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".nexus-dm")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_ENDPOINT = "https://intersect.nationalsciencedatafabric.org/nexus/api/v1/darkmatter/gen-url"
DEFAULT_CONFIG = {"output_dir": "./idx", "endpoint": DEFAULT_ENDPOINT}


def load_config() -> Dict[str, str]:
    """
    Load the global CLI configuration, creating it with defaults if missing
    """
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception:
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    if not isinstance(config, dict):
        config = {}
    if not config.get("output_dir"):
        config["output_dir"] = DEFAULT_CONFIG["output_dir"]
    if not config.get("endpoint"):
        config["endpoint"] = DEFAULT_CONFIG["endpoint"]

    return config


def save_config(config):
    """
    Persist the global CLI configuration as JSON
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def reset_config() -> Dict[str, str]:
    """
    Reset the global CLI configuration to the defaults
    """
    config = dict(DEFAULT_CONFIG)
    save_config(config)
    return config


def get_output_dir() -> str:
    """
    Return the global output directory
    """
    return load_config().get("output_dir", DEFAULT_CONFIG["output_dir"])


def is_valid_endpoint(endpoint: str) -> bool:
    """
    Check that endpoint is a valid http(s) URL
    """
    if not endpoint or not endpoint.strip():
        return False
    if "\x00" in endpoint:
        return False

    return endpoint.startswith(("http://", "https://"))


def get_endpoint() -> str:
    """
    Return the global download endpoint
    """
    return load_config().get("endpoint", DEFAULT_CONFIG["endpoint"])


def set_endpoint(endpoint: str) -> Dict[str, str]:
    """
    Persist a new global download endpoint
    """
    if not is_valid_endpoint(endpoint):
        raise ValueError(f"'{endpoint}' is not a valid endpoint URL")

    config = load_config()
    config["endpoint"] = endpoint
    save_config(config)
    return config


def is_valid_output_dir(output_dir: str) -> bool:
    """
    Check that output_dir is a valid, writable filesystem path
    """
    if not output_dir or not output_dir.strip():
        return False
    if "\x00" in output_dir:
        return False

    path = os.path.abspath(os.path.expanduser(output_dir))
    if os.path.exists(path):
        return os.path.isdir(path) and os.access(path, os.W_OK)

    parent = os.path.dirname(path)
    while parent and not os.path.exists(parent):
        parent = os.path.dirname(parent)

    return bool(parent) and os.path.isdir(parent) and os.access(parent, os.W_OK)


def set_output_dir(output_dir: str) -> Dict[str, str]:
    """
    Persist a new global output directory
    """
    if not is_valid_output_dir(output_dir):
        raise ValueError(f"'{output_dir}' is not a valid output directory")

    config = load_config()
    config["output_dir"] = os.path.expanduser(output_dir)
    save_config(config)
    return config
