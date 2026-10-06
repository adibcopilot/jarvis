import asyncio
from simulation.physics import SimulationEngine

async def main():
    engine = SimulationEngine()
    print("Initial State:")
    print(f"Trq: {engine.state['trq']}, Cur: {engine.state['cur']:.2f}, Temp: {engine.state['t_motor']:.2f}")
    
    print("\nApplying Torque (Load) Spike to 150 Nm")
    engine.apply_user_override("trq", 150.0)
    
    for i in range(1, 11):
        engine.tick()
        print(f"Tick {i:2d} -> Trq: {engine.state['trq']:.1f}, Cur: {engine.state['cur']:.2f}, Temp: {engine.state['t_motor']:.2f}")

    print("\nCorrupting Temperature Sensor (Spike to 150C) while maintaining physical state:")
    engine.apply_corruption("t_motor", "spike", 150.0)
    readings = engine.get_readings()
    print(f"True Temp: {engine.state['t_motor']:.2f}, Reported Temp: {readings['t_motor']:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
