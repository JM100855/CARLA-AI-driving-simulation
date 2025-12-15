import carla
from carla_simulation import start_carla, stop_carla, run_scenario

# ============================================================
# LOCAL TEST RUNNER
# ============================================================
if __name__ == "__main__":

    # Choose scenario and driver state manually
    scenario_id = 6        # Scenario 1 --> 7
    driver_class = "critical drowsiness"  # alert / slightly drowsy / very drowsy / critical drowsiness
    town = "Town04"         # Town01 / Town04 / Town05

    print("\n===== STARTING LOCAL SIMULATION TEST =====")
    print(f"Scenario: {scenario_id}")
    print(f"Driver state: {driver_class}")
    print(f"Town: {town}")
    print("===========================================\n")

    # 1. Launch CARLA
    carla_process = start_carla()

    try:
        # 2. Connect to CARLA server
        client = carla.Client("localhost", 2000)
        client.set_timeout(60.0)

        print("Connected to CARLA. Running scenario...\n")

        # 3. Run simulation
        run_scenario(client,town,scenario_id,driver_class)

    except Exception as e:
        print("\nERROR DURING SIMULATION:")
        print(str(e))

    finally:
        # 4. Stop CARLA
        print("\nStopping CARLA...")
        stop_carla(carla_process)
        print("CARLA Stopped.")
        print("\n===== TEST COMPLETE =====\n")