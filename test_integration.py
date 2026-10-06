import asyncio
from simulation.physics import physics_engine
from database.db import get_pending_events

async def main():
    # Start loop in background
    task = asyncio.create_task(physics_engine.run_loop())
    
    print("Waiting for physics loop to start...")
    await asyncio.sleep(1.0)
    
    print("Applying Mechanical Jam...")
    physics_engine.apply_user_override("trq", 200.0)
    physics_engine.apply_user_override("cur", 60.0)
    physics_engine.apply_user_override("spd_m", 500.0)
    
    await asyncio.sleep(3.0)
    
    print("Checking database for pending events...")
    events = get_pending_events()
    for e in events:
        if e['event_type'] == 'simulation':
            print(f"FOUND EVENT: {e['category']} - {e['severity']}")
            print(f"Action: {e['proposed_action']}")
            
    print("Test complete. Killing loop.")
    task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
