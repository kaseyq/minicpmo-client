import yaml
import os

def load_config():
    """Load configuration from conf.yaml in the project root."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conf.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise RuntimeError(f"Invalid YAML in {config_path}: {str(e)}")

# Load configuration at module import time
config = load_config()