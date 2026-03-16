import yaml
from pathlib import Path

ROOT = Path(__file__).parent.parent


def load_config():
    with open(ROOT / 'config.yaml') as f:
        return yaml.safe_load(f)


cfg = load_config()
