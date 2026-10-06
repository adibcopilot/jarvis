from agent.reasoner import classify_event

def print_result(desc, state):
    print(f"\n--- {desc} ---")
    res = classify_event("simulation", extra_data=state)
    print(f"Fault: {res['fault']}")
    print(f"Severity: {res['severity']}")
    print(f"Action: {res['proposed_action']}")
    print(f"Reason: {res['reasoning']}")

# Test 1: Motor Overheating (True Heat)
state1 = {
    "t_motor": 130.0,
    "c_flow": 100.0,
    "cur": 30.0, # Elevated current (secondary effect)
    "trq": 90.0, # Elevated load
}
print_result("Motor Overheating Test", state1)

# Test 2: Sensor Drift (Lying Sensor)
state2 = {
    "t_motor": 130.0,
    "c_flow": 100.0,
    "cur": 10.0, # Normal current
    "trq": 50.0, # Normal load
}
print_result("Sensor Drift Test", state2)

