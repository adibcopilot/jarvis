from agent.reasoner import _classify_simulation

def assert_fault(state, expected_fault, expected_cause):
    res = _classify_simulation(state)
    assert res['fault'] == expected_fault, f"Expected {expected_fault}, got {res['fault']} (state={state})"
    assert res['root_cause'] == expected_cause, f"Expected {expected_cause}, got {res['root_cause']} for {expected_fault}"

def main():
    # 0. Nominal
    assert_fault(
        {"t_motor": 40.0, "c_flow": 100.0, "vib": 1.0, "vib_pat": "nominal", "trq": 50.0, "spd_m": 1500.0, "spd_b": 1500.0, "cur": 10.0, "vol": 400.0, "cur_leak": 2.0},
        "Nominal", "Unknown"
    )

    # 1. Motor Overheating
    assert_fault(
        {"t_motor": 105.0, "c_flow": 100.0, "vib": 1.0, "vib_pat": "nominal", "trq": 70.0, "spd_m": 1500.0, "spd_b": 1500.0, "cur": 20.0, "vol": 400.0, "cur_leak": 2.0},
        "Motor Overheating", "Mechanical"
    )

    # 2. Cooling Failure
    assert_fault(
        {"t_motor": 105.0, "c_flow": 0.0, "vib": 1.0, "vib_pat": "nominal", "trq": 50.0, "spd_m": 1500.0, "spd_b": 1500.0, "cur": 10.0, "vol": 400.0, "cur_leak": 2.0},
        "Cooling Failure", "Mechanical"
    )

    # 3. Bearing wear (harmonic)
    assert_fault(
        {"t_motor": 50.0, "c_flow": 100.0, "vib": 5.0, "vib_pat": "harmonic", "trq": 50.0, "spd_m": 1500.0, "spd_b": 1500.0, "cur": 10.0, "vol": 400.0, "cur_leak": 2.0},
        "Bearing Wear", "Mechanical"
    )

    # 4. Shaft misalignment (random)
    assert_fault(
        {"t_motor": 50.0, "c_flow": 100.0, "vib": 5.0, "vib_pat": "random", "trq": 50.0, "spd_m": 1500.0, "spd_b": 1500.0, "cur": 10.0, "vol": 400.0, "cur_leak": 2.0},
        "Shaft Misalignment", "Mechanical"
    )

    # 5. Mechanical Jam (High Trq/Cur, low non-zero spd)
    assert_fault(
        {"t_motor": 40.0, "c_flow": 100.0, "vib": 1.0, "vib_pat": "nominal", "trq": 160.0, "spd_m": 800.0, "spd_b": 800.0, "cur": 35.0, "vol": 400.0, "cur_leak": 2.0},
        "Mechanical Jam", "Mechanical"
    )

    # 6. Lubrication failure (friction heat creep, elevated vib, slight drag)
    assert_fault(
        {"t_motor": 55.0, "c_flow": 100.0, "vib": 3.0, "vib_pat": "nominal", "trq": 60.0, "spd_m": 1500.0, "spd_b": 1500.0, "cur": 15.0, "vol": 400.0, "cur_leak": 2.0},
        "Lubrication Failure", "Human/Manual"
    )

    # 7. Belt slippage
    assert_fault(
        {"t_motor": 40.0, "c_flow": 100.0, "vib": 1.0, "vib_pat": "nominal", "trq": 50.0, "spd_m": 1500.0, "spd_b": 1200.0, "cur": 10.0, "vol": 400.0, "cur_leak": 2.0},
        "Belt Slippage", "Mechanical"
    )

    # 8. Motor Overload (High current/trq, no jam)
    assert_fault(
        {"t_motor": 55.0, "c_flow": 100.0, "vib": 1.0, "vib_pat": "nominal", "trq": 150.0, "spd_m": 1500.0, "spd_b": 1500.0, "cur": 33.0, "vol": 400.0, "cur_leak": 2.0},
        "Motor Overload", "Human/Manual"
    )

    # 9. Voltage fluctuation
    assert_fault(
        {"t_motor": 40.0, "c_flow": 100.0, "vib": 1.0, "vib_pat": "nominal", "trq": 50.0, "spd_m": 1500.0, "spd_b": 1500.0, "cur": 15.0, "vol": 300.0, "cur_leak": 2.0},
        "Voltage Fluctuation", "Environmental"
    )

    # 10. Insulation breakdown
    assert_fault(
        {"t_motor": 40.0, "c_flow": 100.0, "vib": 1.0, "vib_pat": "nominal", "trq": 50.0, "spd_m": 1500.0, "spd_b": 1500.0, "cur": 10.0, "vol": 400.0, "cur_leak": 40.0},
        "Insulation Breakdown", "Environmental"
    )

    # 11. Sensor Drift
    assert_fault(
        {"t_motor": 150.0, "c_flow": 100.0, "vib": 1.0, "vib_pat": "nominal", "trq": 50.0, "spd_m": 1500.0, "spd_b": 1500.0, "cur": 10.0, "vol": 400.0, "cur_leak": 2.0},
        "Sensor Drift", "Technical"
    )

    # 12. Signal Dropout
    assert_fault(
        {"t_motor": 40.0, "c_flow": 100.0, "vib": 1.0, "vib_pat": "nominal", "trq": 50.0, "spd_m": 0.0, "spd_b": 1500.0, "cur": 10.0, "vol": 400.0, "cur_leak": 2.0},
        "Signal Dropout", "Technical"
    )

    print("All assertions passed! 12 faults disambiguated correctly.")

if __name__ == "__main__":
    main()
