"""
Specific guardrail rules definition.
"""

def is_action_allowed(action_type: str, policy_permission: str) -> bool:
    """
    Check if an action is explicitly allowed by the policy.
    """
    if policy_permission == "prohibited":
        return False
    # If approval_required, it's conditionally allowed but must go to approval queue
    if policy_permission in ["allowed", "approval_required"]:
        return True
    return False

def requires_approval(action_type: str, policy_permission: str) -> bool:
    """
    Check if an action explicitly requires human approval.
    """
    return policy_permission == "approval_required"
