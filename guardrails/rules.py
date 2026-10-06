"""
Specific guardrail rules definition.
"""
import re

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

def evaluate_chat_guardrail(query: str) -> dict:
    """
    Evaluates conversational inputs against safety policies.
    - Permits project inquiries, safety policies, architecture questions, and event queries.
    - Prohibits unauthorized physical actuation, prompt injections, and database destruction.
    """
    q = (query or "").lower().strip()
    
    # 1. Prohibited: Database deletion / audit alteration
    destructive_patterns = [
        r"\b(delete|drop|truncate|erase|clear)\b.*\b(database|db|events?|audit|hash|trail|records?)\b",
        r"\b(modify|change|edit)\b.*\b(hash\s*chain|audit\s*trail|sqlite)\b"
    ]
    for pat in destructive_patterns:
        if re.search(pat, q):
            return {
                "allowed": False,
                "reason": "Database alteration and audit log deletion are strictly prohibited by Guardrail policy [database.allow_delete_events: false].",
                "policy": "delete_audit_trail",
                "action_type": "database_deletion"
            }

    # 2. Prohibited: Bypassing human approval or safety guardrails
    bypass_patterns = [
        r"\b(bypass|skip|ignore|override|disable|turn off|remove)\b.*\b(approval|human gate|guardrails?|safety|rules?)\b",
        r"\bexecute\b.*\bwithout\b.*\b(approval|human|authorization)\b"
    ]
    for pat in bypass_patterns:
        if re.search(pat, q):
            return {
                "allowed": False,
                "reason": "Bypassing human approval or disabling safety guardrails is strictly prohibited [llm.can_modify_guardrails: false].",
                "policy": "bypass_human_approval",
                "action_type": "safety_bypass"
            }

    # 3. Prohibited: Direct physical hardware actuation
    hardware_patterns = [
        r"\b(control|actuate|start|stop|run)\b.*\b(physical|real|live)\b.*\b(hardware|plc|robot|actuator|factory)\b",
        r"\bconnect\b.*\b(real|physical)\b.*\b(plc|sensor|camera|machine)\b"
    ]
    for pat in hardware_patterns:
        if re.search(pat, q):
            return {
                "allowed": False,
                "reason": "Direct physical hardware actuation is prohibited. JARVIS is strictly operating within a software simulation environment [actions.physical_hardware_control: prohibited].",
                "policy": "physical_hardware_control",
                "action_type": "hardware_actuation"
            }

    # 4. Allowed: Informational project inquiries, event queries, architecture explanations
    return {
        "allowed": True,
        "reason": "Project information inquiry and natural language explanation approved under policy [actions.project_inquiry: allowed].",
        "policy": "project_inquiry",
        "action_type": "project_inquiry"
    }
