"""
Validator for intercepting proposed actions before execution or approval.
"""
from .policy import get_action_permission
from .rules import is_action_allowed, requires_approval
import logging

logger = logging.getLogger("jarvis.guardrails")

class GuardrailException(Exception):
    pass

def validate_action(action_type: str, action_details: dict) -> dict:
    """
    Validates a proposed action against local security policies.
    Returns a dict with validation status.
    """
    permission = get_action_permission(action_type)
    
    if not is_action_allowed(action_type, permission):
        logger.warning(f"Guardrail Blocked: {action_type} is prohibited by policy.")
        raise GuardrailException(f"Action '{action_type}' is prohibited by system guardrails.")
        
    approval_needed = requires_approval(action_type, permission)
    
    return {
        "status": "validated",
        "action_type": action_type,
        "requires_approval": approval_needed,
        "policy_applied": permission
    }
