import asyncio
import random
from typing import Dict, Any
from datetime import datetime

from agent.reasoner import classify_event
from guardrails.validator import validate_action
from database.db import insert_event
from alerts.email import AUTO_DISPATCHED_STATUS

# Initial / nominal state for all sensors
NOMINAL_STATE = {
    "t_motor": 40.0,       # Motor Temperature (°C)
    "c_flow": 100.0,       # Coolant/Fan Flow Rate (%)
    "vib": 1.0,            # Vibration Level (mm/s)
    "vib_pat": "nominal",  # Vibration Pattern (nominal, harmonic, random)
    "trq": 50.0,           # Shaft Torque (Nm)
    "spd_m": 1500.0,       # Motor Speed (RPM)
    "spd_b": 1500.0,       # Belt Speed (RPM)
    "cur": 10.0,           # Supply Current (Amps)
    "vol": 400.0,          # Supply Voltage (Volts)
    "cur_leak": 2.0,       # Leakage Current (mA)
}

# The physical limits where the machine cannot exceed or physically breaks immediately
PHYSICS_LIMITS = {
    "t_motor": {"min": 20.0, "max": 250.0},
    "c_flow": {"min": 0.0, "max": 100.0},
    "vib": {"min": 0.0, "max": 50.0},
    "trq": {"min": 0.0, "max": 200.0},
    "spd_m": {"min": 0.0, "max": 1600.0},
    "spd_b": {"min": 0.0, "max": 1600.0},
    "cur": {"min": 0.0, "max": 100.0},
    "vol": {"min": 0.0, "max": 500.0},
    "cur_leak": {"min": 0.0, "max": 100.0},
}

class SimulationEngine:
    def __init__(self):
        self.state = NOMINAL_STATE.copy()
        
        # User manipulation overrides (what the user is forcing the sensor to)
        # e.g. {"trq": 150.0} means user is holding the jam injector
        self.overrides: Dict[str, float] = {}
        
        # Corrupted sensors (sensor lies)
        # e.g. {"t_motor": {"type": "spike", "value": 150.0}}
        self.corruptions: Dict[str, Dict[str, Any]] = {}
        
        self.is_running = False
        self.last_diagnosis_fault = "Nominal"

    def apply_user_override(self, sensor: str, value: float):
        if value is None:
            self.overrides.pop(sensor, None)
        else:
            self.overrides[sensor] = value

    def apply_corruption(self, sensor: str, corr_type: str, value: float = None):
        if corr_type == "none":
            self.corruptions.pop(sensor, None)
        else:
            self.corruptions[sensor] = {"type": corr_type, "value": value}

    def _clamp(self, val: float, sensor: str) -> float:
        if sensor in PHYSICS_LIMITS:
            return max(PHYSICS_LIMITS[sensor]["min"], min(val, PHYSICS_LIMITS[sensor]["max"]))
        return val

    def tick(self):
        """Advance the physics simulation by one time step (~1 second)."""
        
        # 1. Apply user overrides directly to physical state first
        for s, v in self.overrides.items():
            self.state[s] = v

        # 2. Coupling Rules (Cascading Effects)
        
        # Load -> Electrical
        # Base current is ~10A. Every 10Nm torque above 50Nm adds 2A current.
        if "cur" not in self.overrides:
            trq_excess = max(0, self.state["trq"] - 50.0)
            target_cur = 10.0 + (trq_excess * 0.2)
            
            # Voltage fluctuation affects current (P = V*I roughly, if V drops, I spikes to maintain power)
            if self.state["vol"] < 400.0 and self.state["vol"] > 0:
                target_cur *= (400.0 / self.state["vol"])
                
            self.state["cur"] += (target_cur - self.state["cur"]) * 0.5 # Smooth transition

        # Electrical -> Thermal
        # Base temp is ~40C. High current generates heat.
        if "t_motor" not in self.overrides:
            # Heat generation factor based on current squared (I^2 R losses)
            heat_gen = (self.state["cur"] / 10.0) ** 2 * 0.5
            
            # Friction heat from vibration
            heat_gen += (self.state["vib"] - 1.0) * 0.2
            
            # Cooling factor based on coolant flow
            cooling = (self.state["c_flow"] / 100.0) * 0.5
            
            # Temperature changes slowly
            self.state["t_motor"] += (heat_gen - cooling)
            
            # Ambient drift
            if heat_gen <= cooling:
                self.state["t_motor"] -= (self.state["t_motor"] - 40.0) * 0.05

        # Friction / Wear
        if "vib" not in self.overrides:
            # Vibration naturally stays around 1.0 unless wear accumulates
            pass

        # 3. Clamp all physical values to realistic limits
        for s in self.state:
            if isinstance(self.state[s], (int, float)):
                self.state[s] = self._clamp(self.state[s], s)

    def get_readings(self) -> Dict[str, Any]:
        """Return the sensor readings, applying corruptions (lies) on top of physical state."""
        readings = self.state.copy()
        
        for sensor, corr in self.corruptions.items():
            if corr["type"] == "spike":
                readings[sensor] = corr["value"]
            elif corr["type"] == "dropout":
                readings[sensor] = 0.0
            elif corr["type"] == "noise":
                base = readings[sensor]
                readings[sensor] = base + (random.random() * base * 0.5)
                
        return readings

    async def run_loop(self):
        self.is_running = True
        while self.is_running:
            self.tick()
            
            # Integration with Reasoner & Guardrails
            readings = self.get_readings()
            decision = classify_event("simulation", extra_data=readings)
            current_fault = decision.get("fault", "Nominal")
            
            # Only log if the diagnosis has changed (threshold crossing / new fault)
            if current_fault != self.last_diagnosis_fault:
                self._log_event(readings, decision, current_fault)
                self.last_diagnosis_fault = current_fault
                
            await asyncio.sleep(1.0)
            
    def _log_event(self, readings: Dict[str, Any], decision: Dict[str, Any], current_fault: str):
        if current_fault == "Nominal":
            return # Don't log recovery yet to save spam, or log a simple recovery event
            
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
        
        # Check guardrails
        # If it's a technical sensor issue, it might auto-resolve. 
        # If it's mechanical/electrical, it needs approval.
        requires_approval = (category in ["mechanical", "electrical"])
        
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
