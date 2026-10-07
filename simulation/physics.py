import asyncio
import random
from typing import Dict, Any
from datetime import datetime

from agent.reasoner import classify_event
from guardrails.validator import validate_action
from database.db import insert_event
from alerts.email import AUTO_DISPATCHED_STATUS

# SIMULATION PARAMETERS, NOT REAL INDUSTRIAL FIGURES
SIMULATION_THRESHOLDS = {
    "vol_nominal": 400.0,
    "vol_deviation_pct": 10.0, # 10% deviation is a fault
    "insulation_fault_ma": 30.0, # Leakage > 30mA is fault
    "belt_slip_pct": 10.0, # Belt speed > 10% below motor speed
    "t_motor_high": 100.0,
    "t_motor_critical": 120.0,
    "vib_high": 10.0,
    "trq_high": 120.0,
    "c_flow_low": 20.0
}

class SimulationEngine:
    def __init__(self):
        # 1. True Physical State
        self.state = {
            "t_motor": 40.0,
            "c_flow": 100.0,
            "vib": 1.0,
            "vib_pat": "nominal",
            "trq": 50.0,
            "spd_m": 1500.0,
            "spd_b": 1500.0,
            "cur": 10.0,
            "vol": 400.0,
            "cur_leak": 2.0,
        }
        
        # 2. Controls (User inputs/causes)
        self.controls = {
            "load_demand": 50.0,       # Drives Trq
            "coolant_flow": 100.0,     # Drives C_flow
            "ambient_temp": 40.0,      # Baseline temp
            "supply_voltage": 400.0,   # Drives Vol
            "jam_injector": False,     # Boolean hold
            "bearing_wear_btn": False, # Boolean hold (accumulates wear)
            "shaft_offset": 0.0,       # Slider (0-100) -> Adds random vib
            "lubricant_level": 100.0,  # Slider (0-100) -> Low adds friction/heat
            "belt_tension": 100.0,     # Slider (0-100) -> Low drops Spd_b
            "insulation_health": 100.0 # Slider (0-100) -> Low increases Cur_leak
        }
        
        # Hidden accumulation variables
        self._accumulated_wear = 0.0
        
        # 3. Corrupted sensors (lies)
        # e.g. {"t_motor": {"type": "spike", "value": 150.0}}
        # For drift, we keep track of the current drift offset
        self.corruptions: Dict[str, Dict[str, Any]] = {}
        self.frozen_values: Dict[str, float] = {}
        
        self.is_running = False
        self.last_diagnosis_fault = "Nominal"

    def apply_control(self, control: str, value: Any):
        if control in self.controls:
            self.controls[control] = value

    def apply_corruption(self, sensor: str, corr_type: str, value: float = None):
        if corr_type == "none":
            self.corruptions.pop(sensor, None)
            self.frozen_values.pop(sensor, None)
        else:
            self.corruptions[sensor] = {"type": corr_type, "value": value, "drift_offset": 0.0}
            if corr_type == "freeze":
                # Snapshot current reported value
                self.frozen_values[sensor] = self.get_readings().get(sensor, 0.0)

    def tick(self):
        """Advance the physics simulation by one time step (~1 second)."""
        
        # Apply Wear Accumulation
        if self.controls["bearing_wear_btn"]:
            self._accumulated_wear += 0.5
            
        # 1. Base Variables from Controls
        self.state["vol"] = self.controls["supply_voltage"]
        self.state["c_flow"] = self.controls["coolant_flow"]
        
        # Insulation
        # As health drops from 100 to 0, leak increases from 2.0 to 50.0
        leak_factor = max(0, 100.0 - self.controls["insulation_health"]) / 100.0
        self.state["cur_leak"] = 2.0 + (leak_factor * 48.0)
        
        # Jam Injector vs Normal Load
        if self.controls["jam_injector"]:
            self.state["trq"] = 160.0
            self.state["spd_m"] = 800.0 # Stays above small nonzero floor
        else:
            # Base torque is load demand + slight drag from low lubricant
            lube_drag = max(0, (100.0 - self.controls["lubricant_level"]) * 0.1)
            self.state["trq"] = self.controls["load_demand"] + lube_drag
            self.state["spd_m"] = 1500.0
            
        # Belt Tension
        # If tension < 50, belt slips
        if self.controls["belt_tension"] < 50.0:
            self.state["spd_b"] = self.state["spd_m"] * 0.8 # 20% slip
        else:
            self.state["spd_b"] = self.state["spd_m"]
            
        # 2. Coupling Rules
        
        # Load -> Electrical Current
        # Base current ~10A. High torque needs more current.
        trq_excess = max(0, self.state["trq"] - 50.0)
        target_cur = 10.0 + (trq_excess * 0.4)
        
        # Voltage drop increases current to maintain power
        if self.state["vol"] > 0 and self.state["vol"] < 400.0:
            target_cur *= (400.0 / self.state["vol"])
            
        self.state["cur"] += (target_cur - self.state["cur"]) * 0.5
        
        # Vibration Logic
        # Bearing wear adds harmonic vib. Shaft offset adds random vib. Low lube adds general vib.
        vib_lube = max(0, (100.0 - self.controls["lubricant_level"]) * 0.03)
        vib_offset = (self.controls["shaft_offset"] / 100.0) * 6.0
        
        total_vib = 1.0 + self._accumulated_wear + vib_offset + vib_lube
        self.state["vib"] = min(50.0, total_vib)
        
        if self._accumulated_wear > vib_offset:
            self.state["vib_pat"] = "harmonic"
        elif vib_offset > 0.5:
            self.state["vib_pat"] = "random"
        else:
            self.state["vib_pat"] = "nominal"
            
        # Thermal Logic (Electrical + Friction)
        heat_gen = (self.state["cur"] / 10.0) ** 2 * 0.4
        heat_gen += vib_lube * 1.5
        cooling = (self.state["c_flow"] / 100.0) * 0.5
        ambient = self.controls["ambient_temp"]
        
        self.state["t_motor"] += (heat_gen - cooling)
        
        # Ambient drift
        if heat_gen <= cooling:
            self.state["t_motor"] -= (self.state["t_motor"] - ambient) * 0.1

    def get_readings(self) -> Dict[str, Any]:
        """Return the reported sensor readings, applying corruptions (lies)."""
        readings = self.state.copy()
        
        for sensor, corr in self.corruptions.items():
            if corr["type"] == "spike":
                readings[sensor] = corr["value"]
            elif corr["type"] == "dropout":
                readings[sensor] = 0.0
            elif corr["type"] == "freeze":
                readings[sensor] = self.frozen_values.get(sensor, readings[sensor])
            elif corr["type"] == "drift":
                corr["drift_offset"] += 2.5 # drifts 2.5 units per tick
                if isinstance(readings[sensor], (int, float)):
                    readings[sensor] += corr["drift_offset"]
            elif corr["type"] == "noise":
                base = readings[sensor]
                if isinstance(base, (int, float)):
                    readings[sensor] = base + (random.random() * base * 0.5)
                
        return readings

    def apply_fix(self, fix_action: str, source: str = "User"):
        fix_action_lower = fix_action.lower()
        if "recalibrate" in fix_action_lower or "restart sensor" in fix_action_lower:
            self.corruptions.clear()
            self.frozen_values.clear()
        elif "soft reset" in fix_action_lower:
            self.corruptions.clear()
            self.frozen_values.clear()
        elif "cooling override" in fix_action_lower:
            self.controls["coolant_flow"] = 100.0
        elif "emergency stop" in fix_action_lower or "halt motor" in fix_action_lower or "halt line" in fix_action_lower:
            self.controls["load_demand"] = 0.0
            self.controls["jam_injector"] = False
        elif "part swap" in fix_action_lower or "bearings" in fix_action_lower:
            self._accumulated_wear = 0.0
            self.controls["bearing_wear_btn"] = False
        elif "re-lubricate" in fix_action_lower:
            self.controls["lubricant_level"] = 100.0
        elif "re-tension" in fix_action_lower:
            self.controls["belt_tension"] = 100.0
        elif "re-insulate" in fix_action_lower:
            self.controls["insulation_health"] = 100.0
        elif "backup power" in fix_action_lower:
            self.controls["supply_voltage"] = 400.0
            
        # Logging rule: append to the hash-chained log on user fix and JARVIS fix.
        insert_event(
            event_type="simulation",
            source_file="Interactive Simulation",
            detections=[{"label": f"{source} Fix Applied", "confidence": 1.0, "fix": fix_action}],
            severity="info",
            category="fix",
            proposed_action="None",
            approval_status=AUTO_DISPATCHED_STATUS,
            approved_by=source,
            resolved_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

    async def run_loop(self):
        self.is_running = True
        while self.is_running:
            self.tick()
            
            readings = self.get_readings()
            decision = classify_event("simulation", extra_data=readings)
            current_fault = decision.get("fault", "Nominal")
            
            if current_fault != self.last_diagnosis_fault:
                self._log_event(readings, decision, current_fault)
                self.last_diagnosis_fault = current_fault
                
            await asyncio.sleep(1.0)
            
    def _log_event(self, readings: Dict[str, Any], decision: Dict[str, Any], current_fault: str):
        if current_fault == "Nominal":
            insert_event(
                event_type="simulation",
                source_file="Interactive Simulation",
                detections=[{"label": "Recovery", "confidence": 1.0, "readings": readings}],
                severity="info",
                category="none",
                proposed_action="None",
                approval_status=AUTO_DISPATCHED_STATUS,
                approved_by="autonomous: recovery",
                resolved_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            return
            
        severity = decision.get("severity", "low")
        category = decision.get("category", "technical")
        
        observation = {
            "label": "simulation_sample",
            "confidence": 1.0,
            "readings": readings,
            "source": "physics_engine"
        }
        decision_record = {
            "label": "autonomous_decision",
            "confidence": 1.0,
            "fault": current_fault,
            "reasoning": decision.get("reasoning", "")
        }
        
        action_mapping = {
            "technical": "sensor_fixes",
            "mechanical": "mechanical_fixes",
            "electrical": "electrical_fixes"
        }
        mapped_action = action_mapping.get(category, "simulated_equipment_control")
        
        try:
            val_result = validate_action(mapped_action, {})
            requires_approval = val_result.get("requires_approval", True)
        except Exception:
            requires_approval = True
            
        if requires_approval:
            insert_event(
                event_type="simulation",
                source_file="Interactive Simulation",
                detections=[observation, decision_record],
                severity=severity,
                category=category,
                proposed_action=decision.get("proposed_action", ""),
                approval_status="pending"
            )
        else:
            # Auto-resolve using the engine if allowed without approval
            self.apply_fix(decision.get("proposed_action", ""))
            insert_event(
                event_type="simulation",
                source_file="Interactive Simulation",
                detections=[observation, decision_record],
                severity=severity,
                category=category,
                proposed_action=decision.get("proposed_action", ""),
                approval_status=AUTO_DISPATCHED_STATUS,
                approved_by="autonomous: simulation_policy",
                resolved_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

physics_engine = SimulationEngine()
