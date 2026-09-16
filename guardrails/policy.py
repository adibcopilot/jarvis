import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.yaml"

def load_policy():
    """Load the guardrails configuration policy."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Guardrails config not found: {CONFIG_PATH}")
        
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def can_llm_execute():
    policy = load_policy()
    return policy.get("llm", {}).get("can_execute_actions", False)

def get_action_permission(action_type: str) -> str:
    policy = load_policy()
    return policy.get("actions", {}).get(action_type, "prohibited")
