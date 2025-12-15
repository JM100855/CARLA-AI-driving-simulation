import carla
import time
import csv
import math
import os
import shutil
import subprocess
import psutil
import pygame
import keyboard

# ---------------------------------------------------------
# Variables Initialization
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARLA_PATH = os.path.join(BASE_DIR, "CARLA_0.9.16", "CarlaUE4.exe")
pygame.mixer.init()
beep_soft = pygame.mixer.Sound("assets/audio/softbeep.wav")
beep_heavy = pygame.mixer.Sound("assets/audio/heavybeep.wav")
cancel_sound = pygame.mixer.Sound("assets/audio/cancelled.wav")
flasher_sound = pygame.mixer.Sound("assets/audio/flasher.wav")
scenario3_sound = pygame.mixer.Sound("assets/audio/scenario3.wav")
scenario4_sound = pygame.mixer.Sound("assets/audio/scenario4.wav")
scenario5_sound = pygame.mixer.Sound("assets/audio/scenario5.wav")
scenario6_sound = pygame.mixer.Sound("assets/audio/scenario6.wav")
HAZARD = carla.VehicleLightState.LeftBlinker | carla.VehicleLightState.RightBlinker

# ---------------------------------------------------------
# Start Carla Process
# ---------------------------------------------------------
def start_carla():
    print("Launching CARLA simulator...")
    process = subprocess.Popen([
        CARLA_PATH,
        "-vulkan",
        "-ResX=640",
        "-ResY=360",
        "-quality-level=Low",
    ])
    print("Waiting 15 seconds for CARLA to load...")
    time.sleep(15)
    return process


# ---------------------------------------------------------
# Stop Carla Process
# ---------------------------------------------------------
def stop_carla(process):
    print("Closing CARLA simulator...")
    try:
        parent = psutil.Process(process.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except:
        pass
    print("CARLA closed.\n")

# ---------------------------------------------------------
# Scenario 1 Urban Driving with Drowsiness Reactions
# ---------------------------------------------------------
def scenario_1_control(vehicle, t, driver_class, driver_ok_pressed):
    """
    Scenario 1 behavior:
    - alert → normal driving
    - slightly drowsy → soft beep after 5 sec
    - very drowsy → hard beep after 5 sec
    - critical drowsiness → looping alert + 3 sec OK window + AI takeover
    """

    # -----------------------------
    # Speed calculation
    # -----------------------------
    vel = vehicle.get_velocity()
    speed = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2) * 3.6
    steer = 0.0

    # -----------------------------
    # Initialize beep timers
    # -----------------------------
    if not hasattr(vehicle, "last_slight_beep"):
        vehicle.last_slight_beep = -999

    if not hasattr(vehicle, "last_very_beep"):
        vehicle.last_very_beep = -999

    # -----------------------------------------------------
    # ALERT (Normal)
    # -----------------------------------------------------
    if driver_class == "alert":
        pass

    # -----------------------------------------------------
    # SLIGHTLY DROWSY
    # -----------------------------------------------------
    elif driver_class == "slightly drowsy":

        first_beep_delay = 5     # first beep after 5 seconds
        interval = 60            # then every 60 seconds

        if t > first_beep_delay and (t - vehicle.last_slight_beep >= interval):
            beep_soft.play()
            vehicle.last_slight_beep = t

    # -----------------------------------------------------
    # VERY DROWSY
    # -----------------------------------------------------
    elif driver_class == "very drowsy":

        first_beep_delay = 5
        interval = 60

        if t > first_beep_delay and (t - vehicle.last_very_beep >= interval):
            beep_heavy.play()
            pygame.time.delay(3000)  # trim to 3 seconds
            beep_heavy.stop()
            vehicle.last_very_beep = t

    # -----------------------------------------------------
    # CRITICAL DROWSINESS
    # -----------------------------------------------------
    elif driver_class == "critical drowsiness":
        # Create persistent flags
        if not hasattr(vehicle, "critical_start"):
            vehicle.critical_start = t
            vehicle.warn_phase = False
            vehicle.critical_resolved = False
            print("CRITICAL: Warning scheduled at t = 5 seconds.")

        # If driver already pressed OK once, behave normally forever
        if vehicle.critical_resolved:
            throttle = 0.45 if speed < 30 else 0.0
            brake = 0.0 if speed < 30 else 0.2
            return steer, throttle, brake, speed

        # BEFORE warning (first 5 sec)
        if t < 5:
            throttle = 0.45 if speed < 30 else 0.0
            brake = 0.0 if speed < 30 else 0.2
            return steer, throttle, brake, speed

        # Start warning once
        if not vehicle.warn_phase:
            vehicle.warn_phase = True
            vehicle.warning_start = t
            print("CRITICAL WARNING: Press O within 3 sec.")

            # start beep
            beep_heavy.play(loops=-1)

            # turn on hazard lights
            vehicle.set_light_state(carla.VehicleLightState(HAZARD))

        warning_elapsed = t - vehicle.warning_start

        # DRIVER PRESSED O during the warning window
        if driver_ok_pressed and warning_elapsed < 3:
            print(">>> DRIVER CONFIRMED OK — continuing normally.")

            # stop beep
            beep_heavy.stop()

            # Cancel Button Sound
            cancel_sound.play()

            # turn off hazards
            vehicle.set_light_state(carla.VehicleLightState.NONE)

            # Permanently resolve critical mode
            vehicle.critical_resolved = True

            throttle = 0.45 if speed < 30 else 0.0
            brake = 0.0 if speed < 30 else 0.2
            return steer, throttle, brake, speed

        # Waiting window (0 to 3 sec)
        if warning_elapsed < 3:
            throttle = 0.45 if speed < 30 else 0.0
            brake = 0.0 if speed < 30 else 0.2
            return steer, throttle, brake, speed

        # AI TAKEOVER (user did not respond)
        if not hasattr(vehicle, "takeover_initial_speed"):
            vehicle.takeover_initial_speed = speed
            vehicle.takeover_start_time = t
            print("AI TAKEOVER ACTIVE – beginning smooth slowdown.")

        # total time to reduce speed to zero
        slowdown_duration = 5.0  

        elapsed = t - vehicle.takeover_start_time

        # compute desired target speed (linear decay)
        initial = vehicle.takeover_initial_speed
        decel_rate = initial / slowdown_duration
        target_speed = max(0.0, initial - decel_rate * elapsed)

        # compute throttle / brake forces to match target speed smoothly
        if speed > target_speed:
            throttle = 0.0
            brake = min(1.0, (speed - target_speed) / initial)
        else:
            throttle = 0.05
            brake = 0.0

        return steer, throttle, brake, speed


    # -----------------------------------------------------
    # DEFAULT SPEED CONTROL (alert, slightly, very)
    # -----------------------------------------------------
    if speed < 30:
        throttle = 0.45
        brake = 0.0
    else:
        throttle = 0.0
        brake = 0.2

    return steer, throttle, brake, speed

# ---------------------------------------------------------
# Scenario 2 Highway Driving with Drowsiness Reactions
# ---------------------------------------------------------
def scenario_2_control(vehicle, t, driver_class, driver_ok_pressed, world):
    """
    Scenario 2 behavior:
    - alert → normal driving
    - slightly drowsy → soft beep after 5 sec
    - very drowsy → hard beep after 5 sec
    - critical drowsiness → warning + 3 sec OK window
        If user does NOT respond:
            AI maintains highway speed until reaching safe area
            then performs smooth stop
    """
    vel = vehicle.get_velocity()
    speed = (vel.x**2 + vel.y**2 + vel.z**2)**0.5 * 3.6
    steer = 0.0

    if not hasattr(vehicle, "last_slight_beep"):
        vehicle.last_slight_beep = -999

    if not hasattr(vehicle, "last_very_beep"):
        vehicle.last_very_beep = -999

    if driver_class == "alert":
        pass

    elif driver_class == "slightly drowsy":
        if t > 5 and (t - vehicle.last_slight_beep >= 60):
            beep_soft.play()
            vehicle.last_slight_beep = t

    elif driver_class == "very drowsy":
        if t > 5 and (t - vehicle.last_very_beep >= 60):
            beep_heavy.play()
            pygame.time.delay(3000)
            beep_heavy.stop()
            vehicle.last_very_beep = t

    elif driver_class == "critical drowsiness":
        # Initialize critical state
        if not hasattr(vehicle, "critical_start"):
            vehicle.critical_start = t
            vehicle.warn_phase = False
            vehicle.critical_resolved = False
            print("CRITICAL: Warning scheduled at t = 5 seconds.")

        # If driver already pressed OK, behave normally forever
        if vehicle.critical_resolved:
            throttle = 0.55 if speed < 90 else 0.0
            brake = 0.0 if speed < 90 else 0.2
            return steer, throttle, brake, speed

        # BEFORE warning (first 5 sec)
        if t < 5:
            throttle = 0.55 if speed < 90 else 0.0
            brake = 0.0 if speed < 90 else 0.2
            return steer, throttle, brake, speed

        # Start warning once
        if not vehicle.warn_phase:
            vehicle.warn_phase = True
            vehicle.warning_start = t
            print("CRITICAL WARNING: Press O within 3 sec.")

            # Start beep
            beep_heavy.play(loops=-1)

            # Turn on hazard lights
            vehicle.set_light_state(carla.VehicleLightState(HAZARD))

        warning_elapsed = t - vehicle.warning_start

        # DRIVER PRESSED O during warning window
        if driver_ok_pressed and warning_elapsed < 3:
            print(">>> DRIVER CONFIRMED OK — continuing normally.")

            # Stop beep
            beep_heavy.stop()

            # Cancel Button Sound
            cancel_sound.play()

            # Turn off hazards
            vehicle.set_light_state(carla.VehicleLightState.NONE)

            # Permanently resolve critical mode
            vehicle.critical_resolved = True

            throttle = 0.55 if speed < 90 else 0.0
            brake = 0.0 if speed < 90 else 0.2
            return steer, throttle, brake, speed

        # Waiting window (0 to 3 sec)
        if warning_elapsed < 3:
            throttle = 0.55 if speed < 90 else 0.0
            brake = 0.0 if speed < 90 else 0.2
            return steer, throttle, brake, speed

        # AI TAKEOVER - Move to rightmost lane AND stop
        if not hasattr(vehicle, "takeover_start_time"):
            vehicle.takeover_start_time = t
            vehicle.takeover_initial_speed = speed
            print("AI TAKEOVER ACTIVE – moving to rightmost shoulder lane and stopping.")

            # Find THE ABSOLUTE rightmost lane
            current_location = vehicle.get_location()
            current_waypoint = world.get_map().get_waypoint(current_location)
            
            rightmost_waypoint = current_waypoint
            lane_count = 0
            while True:
                right_lane = rightmost_waypoint.get_right_lane()
                if right_lane is not None:
                    rightmost_waypoint = right_lane
                    lane_count += 1
                    print(f"Found lane {lane_count}: type={right_lane.lane_type}")
                else:
                    break
            
            vehicle.target_lane_id = rightmost_waypoint.lane_id
            print(f"Target rightmost lane ID: {vehicle.target_lane_id}")

        # Get current position and lane info
        current_location = vehicle.get_location()
        current_waypoint = world.get_map().get_waypoint(current_location)
        vehicle_transform = vehicle.get_transform()

        # Check if in target lane
        in_target_lane = (current_waypoint.lane_id == vehicle.target_lane_id)
        
        # Calculate distance to lane center
        lane_width = current_waypoint.lane_width
        vehicle_location = vehicle_transform.location
        lane_center = current_waypoint.transform.location
        dx_lane = vehicle_location.x - lane_center.x
        dy_lane = vehicle_location.y - lane_center.y
        lateral_distance = math.sqrt(dx_lane**2 + dy_lane**2)
        
        # Determine target waypoint
        if in_target_lane and lateral_distance < lane_width * 0.5:
            # Centered - follow straight (increased threshold from 0.3 to 0.5)
            lookahead = 10.0
            next_wps = current_waypoint.next(lookahead)
            target_waypoint = next_wps[0] if next_wps else current_waypoint
        else:
            # Need to change lanes or center
            lookahead = 12.0  # Increased from 8.0 to look further ahead
            forward_wp = current_waypoint.next(lookahead)
            forward_wp = forward_wp[0] if forward_wp else current_waypoint
            
            # Get rightmost lane
            target_waypoint = forward_wp
            while True:
                right_lane = target_waypoint.get_right_lane()
                if right_lane is not None:
                    target_waypoint = right_lane
                else:
                    break

        # Calculate steering
        target_location = target_waypoint.transform.location
        dx = target_location.x - vehicle_transform.location.x
        dy = target_location.y - vehicle_transform.location.y
        
        target_angle = math.atan2(dy, dx)
        vehicle_angle = math.radians(vehicle_transform.rotation.yaw)
        angle_diff = target_angle - vehicle_angle
        angle_diff = math.atan2(math.sin(angle_diff), math.cos(angle_diff))
        
        # Steering control
        if in_target_lane and lateral_distance < lane_width * 0.5:
            steer = angle_diff * 0.2
        elif in_target_lane:
            steer = angle_diff * 0.6  # Increased from 0.5 to center more aggressively
        else:
            steer = angle_diff * 0.4
        
        steer = max(-0.5, min(0.5, steer))

        # Speed control
        elapsed = t - vehicle.takeover_start_time
        initial = vehicle.takeover_initial_speed
        
        if in_target_lane and lateral_distance < lane_width * 0.3:
            decel_rate = initial / 6.0
        else:
            decel_rate = initial / 10.0
        
        target_speed = max(0.0, initial - decel_rate * elapsed)

        if speed > target_speed + 2:
            throttle = 0.0
            brake = min(1.0, (speed - target_speed) / 50.0)
        elif speed < target_speed - 2:
            throttle = 0.2
            brake = 0.0
        else:
            throttle = 0.1
            brake = 0.0

        return steer, throttle, brake, speed

    # ----------------------------------------------
    # DEFAULT SPEED LOGIC
    # ----------------------------------------------
    if speed < 90:
        throttle = 0.55
        brake = 0.0
    else:
        throttle = 0.0
        brake = 0.2
    return steer, throttle, brake, speed


# ---------------------------------------------------------
# Scenario 3 Approaching Barrier on Urban Street
# ---------------------------------------------------------
def scenario_3_control(vehicle, t):
    """
    Scenario 3 behavior:
    - normal driving at first
    - vehicle drifts slowly toward the right barrier
    - when the system detects proximity:
          play warning beep once
          begin automatic steering correction
    - AI steers left to bring the car back to the lane center
    - after correction, AI stabilizes steering and continues straight
    """
    vel = vehicle.get_velocity()
    speed = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2) * 3.6

    if not hasattr(vehicle, "beep_played"):
        vehicle.beep_played = False
    if not hasattr(vehicle, "assitant_warning"):
        vehicle.assitant_warning = False

    # === CONTROL LOGIC ===
    if t < 5:
        steer = 0.0

    elif 5 <= t < 6.3:
        # drifting right, but not too aggressively
        steer = 0.03
        if t>= 5.3 and not vehicle.assitant_warning:
            vehicle.assitant_warning = True
            scenario3_sound.play()

    elif 6.3 <= t < 7.5:
        if not vehicle.beep_played:
            vehicle.beep_played = True
            beep_heavy.play()       
        # big correction
        steer = -0.034
    elif 7.5 <= t < 8.3:
        # moderate correction to center lane
        steer = 0.0
    else:
        # stabilize straight
        steer = 0.0
        vehicle.beep_played = False
        beep_heavy.stop()

    # Speed control
    if speed < 30:
        throttle = 0.45
        brake = 0.0
    else:
        throttle = 0.0
        brake = 0.2

    return steer, throttle, brake, speed

# ---------------------------------------------------------
# Scenario 4 Driver switches lanes on a two way street
# ---------------------------------------------------------
def scenario_4_control(vehicle, t):
    """
    Scenario 4 behavior:
    The driver drifts into the wrong lane on a two way street, triggering an AI safety takeover.
    
    - 0 to 5 sec: Normal driving with no warnings.
    - 5 to 7 sec: Vehicle begins drifting. After 6 sec the AI plays a warning beep and
      alerts the driver that they are entering the wrong lane. Hazards turn on.
    - 7 to 9 sec: AI performs an emergency steering correction to guide the car back.
    - 9 to 14 sec: AI stabilizes the vehicle’s path. Beeping stops and hazard flashers continue.
    - 14+ sec: Shared control phase where the vehicle drives straight again and all alerts stop.
    
    The function returns steering, throttle, brake, and speed for each time step,
    allowing the simulation to smoothly transition through alert, correction, and recovery.
    """
    vel = vehicle.get_velocity()
    speed = (vel.x**2 + vel.y**2 + vel.z**2)**0.5 * 3.6

    # Flags for sound logic
    if not hasattr(vehicle, "assitant_started"):
        vehicle.assitant_started = False
    if not hasattr(vehicle, "warning_started"):
        vehicle.warning_started = False
    if not hasattr(vehicle, "stabilized"):
        vehicle.stabilized = False

    # Base throttle for steady speed
    throttle = 0.45
    brake = 0.0

    # -------------------------------
    # 0–5 sec: Normal
    # -------------------------------
    if t < 5:
        steer = 0.0
        vehicle.set_light_state(carla.VehicleLightState.NONE)

    # -------------------------------
    # 5–7 sec: Driver drifting
    # -------------------------------
    elif 5 <= t < 7:
        steer = -0.015
        vehicle.set_light_state(carla.VehicleLightState.NONE)
        if not vehicle.assitant_started:
            vehicle.assitant_started = True
            scenario4_sound.play()
        if t > 6 and not vehicle.warning_started: 
            vehicle.warning_started = True
            beep_heavy.play(loops=-1)
            print("AI ALERT: You are switching into the wrong lane. This is a two way street. Correcting now.")
        vehicle.set_light_state(carla.VehicleLightState(HAZARD))
        return steer, throttle, brake, speed

    # -------------------------------
    # 7–9 sec: AI emergency correction
    # -------------------------------
    elif 7 <= t < 9:
        steer = 0.0205
        return steer, throttle, brake, speed

    # -------------------------------
    # 9–14 sec: Smooth stabilization
    # -------------------------------
    elif 9 <= t < 14:
        if not vehicle.stabilized:
            vehicle.stabilized = True
            beep_heavy.stop()  # stop beep, keep flashers running
            flasher_sound.play(loops=-1)

        steer = -0.0025
        vehicle.set_light_state(carla.VehicleLightState(HAZARD))

    # -------------------------------
    # 11–20 sec: Stable shared control
    # -------------------------------
    else:
        flasher_sound.stop()
        steer = 0.0
        vehicle.set_light_state(carla.VehicleLightState.NONE)

    
    return steer, throttle, brake, speed
    
# ---------------------------------------------------------
# Scenario 5: Driver unresponsive during red light
# ---------------------------------------------------------
def scenario_5_control(vehicle, t, driver_ok_pressed, world):
    """
    Scenario 5: Red light warning
    - 0–9.5s : Normal driving
    - 9.5s  : Warning + 2 sec window
    - If no response: AI takeover gradual stop
    - If user overrides: sound stops + right flasher ON but STILL follow same AI stop curve
    """
    vel = vehicle.get_velocity()
    speed = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2) * 3.6
    steer = 0.0

    # Initialize state
    if not hasattr(vehicle, "s5_warn_phase"):
        vehicle.assistant_warning = False
        vehicle.s5_warn_phase = False
        vehicle.s5_resolved = False            # user override flag
        vehicle.s5_lights_turned_red = False

    # Before warning window
    if t < 9.5:
        if t > 8 and not vehicle.assistant_warning:
            vehicle.assistant_warning = True
            scenario5_sound.play()
        throttle = 0.60 if speed < 40 else 0.0
        brake = 0.0 if speed < 40 else 0.2
        return steer, throttle, brake, speed

    # Turn traffic lights red once
    if not vehicle.s5_lights_turned_red:
        vehicle.s5_lights_turned_red = True
        set_all_traffic_lights(world, "red")
        print("🔴 Traffic lights turned RED at t=9s")

    # Start warning once
    if not vehicle.s5_warn_phase:
        vehicle.s5_warn_phase = True
        vehicle.warning_start = t
        print("⚠️ RED LIGHT AHEAD! Press O within 2 sec!")
        beep_heavy.play(loops=-1)
        vehicle.set_light_state(carla.VehicleLightState(HAZARD))

    warning_elapsed = t - vehicle.warning_start

    # User override DURING the warning window
    if driver_ok_pressed and warning_elapsed < 2:
        if not vehicle.s5_resolved:
            beep_heavy.stop()
            cancel_sound.play()
            vehicle.s5_resolved = True
            vehicle.set_light_state(carla.VehicleLightState.RightBlinker)
            print(">>> USER OVERRIDE — stopping sound, keeping AI stop timing")

    # Waiting window
    if warning_elapsed < 2:
        throttle = 0.60 if speed < 40 else 0.0
        brake = 0.0 if speed < 40 else 0.2
        return steer, throttle, brake, speed

    # -------- AI TAKEOVER (OR USER OVERRIDE) --------
    # Initialize AI takeover timing ONCE
    if not hasattr(vehicle, "takeover_initial_speed"):
        vehicle.takeover_initial_speed = speed
        vehicle.takeover_start_time = t
        print("🤖 AI TAKEOVER — smooth stop engaged")

    # Smooth gradual AI stop
    slowdown_duration = 2.0        # how long the stop lasts
    initial = vehicle.takeover_initial_speed
    elapsed = t - vehicle.takeover_start_time

    target_speed = max(0.0, initial * (1 - elapsed / slowdown_duration))

    # Apply same gentle braking curve whether AI or user override
    if speed > target_speed:
        throttle = 0.0
        brake = min(0.4, (speed - target_speed) / initial)
    else:
        throttle = 0.0
        brake = 0.4

    return steer, throttle, brake, speed

def scenario_6_control(vehicle, npc, t):
    vel = vehicle.get_velocity()
    speed = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2) * 3.6

    steer = 0.0
    throttle = 0.55 if speed < 90 else 0.0
    brake = 0.0

    ego_loc = vehicle.get_location()
    npc_loc = npc.get_location()

    dist = ego_loc.distance(npc_loc)

    # Flags
    if not hasattr(npc, "s6_drift"):
        npc.s6_drift = False
    if not hasattr(vehicle, "s6_warning"):
        vehicle.s6_warning = False
    if not hasattr(vehicle, "s6_evade"):
        vehicle.s6_evade = False
    if not hasattr(vehicle, "s6_return"):
        vehicle.s6_return = False
    if not hasattr(vehicle, "flacher_warning"):
        vehicle.flacher_warning = False

    if dist < 40 and not npc.s6_drift:
        print("🚗💥 NPC is drifting toward your lane!")
        npc.s6_drift = True
    
    if npc.s6_drift:
        ctrl = npc.get_control()
        ctrl.throttle = 0.5
        ctrl.steer = -0.0135
        npc.apply_control(ctrl)

    # === 1. Warning phase ===
    if dist < 50 and not vehicle.s6_warning:
        print("⚠️ Oncoming traffic detected")
        scenario6_sound.play()
        beep_heavy.play(loops=-1)
        vehicle.s6_warning = True
        vehicle.set_light_state(carla.VehicleLightState.RightBlinker)

    # === 2. Emergency deviation ===
    if dist < 25 and not vehicle.s6_evade:
        print("➡️ Slight evasive move to the right")
        vehicle.s6_evade = True
        vehicle.s6_evade_start = t

    # Apply small evasive steer
    if vehicle.s6_evade and not vehicle.s6_return:
        steer = 0.012   # right shift
        throttle = 0.40
        brake = 0.0

        # After 1 sec, start returning to lane center
        if t - vehicle.s6_evade_start > 1:
            vehicle.s6_return = True
            vehicle.s6_return_start = t
        return steer, throttle, brake, speed

    # === 3. Smooth return to center line ===
    if vehicle.s6_return:
        steer = -0.0017   # gentle correction left
        throttle = 0.45
        brake = 0.0

        # After 1 sec, normal driving again
        if t - vehicle.s6_return_start > 1.0:
            steer = 0.0
            vehicle.s6_return = False
            if t > 4 and not vehicle.flacher_warning:
                vehicle.flacher_warning = True
                beep_heavy.stop()
                flasher_sound.play(loops=-1)
            if t > 15:
                vehicle.set_light_state(carla.VehicleLightState.NONE)
                flasher_sound.stop()
        return steer, throttle, brake, speed

    # Default highway cruise
    return steer, throttle, brake, speed


# ---------------------------------------------------------
# FINAL MANUAL SAFE SPAWNS PER TOWN (100 percent reliable)
# ---------------------------------------------------------
def get_fixed_spawn(world, town_name):
    spawn_points = world.get_map().get_spawn_points()

    if not spawn_points:
        raise ValueError(f"No spawn points found for {town_name}.")

    safe_spawn_indices = {
        "Town01": 35,
        "Town04": 19,
        "Town05": 20 
    }

    spawn_index = safe_spawn_indices.get(town_name, 0)
    selected_transform = spawn_points[spawn_index]

    return selected_transform

# ---------------------------------------------------------
# Shift Lane (Left/Right)
# ---------------------------------------------------------
def shift_lane(world, transform, lanes=1):
    # Get waypoint on the road
    m = world.get_map()
    wp = m.get_waypoint(transform.location, project_to_road=True)

    # Lane width
    lane_w = wp.lane_width

    # LEFT = negative right_vector
    offset_vec = wp.transform.get_right_vector() * (-lanes * lane_w)

    new_loc = transform.location + offset_vec
    new_loc.z += 0.1  # prevent clipping

    return carla.Transform(new_loc, transform.rotation)

# ---------------------------------------------------------
# Shift Road (Backward/Forward)
# ---------------------------------------------------------
def shift_along_road(transform, distance):
    """
    Moves a transform forward or backward along its facing direction.
    
    distance > 0 → move later (forward)
    distance < 0 → move earlier (backward)
    """

    yaw = math.radians(transform.rotation.yaw)

    dx = distance * math.cos(yaw)
    dy = distance * math.sin(yaw)

    new_loc = carla.Location(
        x = transform.location.x + dx,
        y = transform.location.y + dy,
        z = transform.location.z
    )

    return carla.Transform(new_loc, transform.rotation)

def set_all_traffic_lights(world, state="green"):
    """
    Set all traffic lights in the world to a specific state.
    
    Args:
        world: CARLA world object
        state: "green", "red", or "yellow"
    """
    traffic_lights = world.get_actors().filter('*traffic_light*')
    
    # Map string to CARLA state
    state_map = {
        "green": carla.TrafficLightState.Green,
        "red": carla.TrafficLightState.Red,
        "yellow": carla.TrafficLightState.Yellow
    }
    
    if state.lower() not in state_map:
        print(f"Invalid state '{state}'. Use 'green', 'red', or 'yellow'")
        return
    
    carla_state = state_map[state.lower()]
    count = 0
    
    for tl in traffic_lights:
        tl.set_state(carla_state)
        tl.freeze(True)
        count += 1
    
    print(f"✅ Set {count} traffic lights to {state.upper()}")

# ---------------------------------------------------------
# Run Scenario
# ---------------------------------------------------------
def run_scenario(client, town_name, scenario_id, driver_class, status_box=None):
    # -----------------------------------------------------
    # INITIAL FOLDER SETUP
    # -----------------------------------------------------
    final_state = driver_class  # updated later for critical cases

    if scenario_id == 1 or scenario_id == 2:
        safe_state = driver_class.replace(" ", "_")
        base_folder = f"output/Scenario{scenario_id}-{town_name}-{safe_state}"
    else:
        base_folder = f"output/Scenario{scenario_id}-{town_name}"

    # Clean old folder
    if os.path.exists(base_folder):
        shutil.rmtree(base_folder)

    os.makedirs(base_folder, exist_ok=True)

    images_folder = os.path.join(base_folder, "images")
    os.makedirs(images_folder, exist_ok=True)

    print(f"\nSaving outputs to: {base_folder}")

    # -----------------------------------------------------
    # LOAD WORLD
    # -----------------------------------------------------
    print(f"\nLoading town: {town_name}")
    world = client.load_world(town_name)
    time.sleep(2)

    # Foce all traffic lights to be green initially
    set_all_traffic_lights(world, "green")

    bp_lib = world.get_blueprint_library()
    vehicle_bp = bp_lib.filter("model3")[0]

    # Spawn vehicle
    spawn_point = get_fixed_spawn(world, town_name)
    npc = None
    if scenario_id == 4:
        spawn_point = shift_lane(world, spawn_point) # Move to the left lane
        spawn_point = shift_along_road(spawn_point,-100) # Move 100 meters to the back
    elif scenario_id == 6:
        npc_bp = bp_lib.filter("vehicle.*model3*")[0]
        npc_spawn = shift_lane(world, spawn_point, +1)     # move to opposite lane
        npc_spawn = shift_along_road(npc_spawn, +120)      # place NPC ahead
        # Fix rotation: align to lane and flip direction toward the ego car
        wp = world.get_map().get_waypoint(npc_spawn.location)
        npc_spawn.rotation.yaw = wp.transform.rotation.yaw + 180
        npc = world.try_spawn_actor(npc_bp, npc_spawn)
        # Make NPC drive toward ego
        npc.set_autopilot(False)
        npc.set_target_velocity(npc.get_transform().get_forward_vector() * 20)
        npc.s6_drift_active = False
        npc.s6_drift_trigger_distance = 40   # start drifting at 40 meters

    vehicle = world.try_spawn_actor(vehicle_bp, spawn_point)
    if not vehicle:
        raise RuntimeError("Failed to spawn vehicle.")
    vehicle.set_autopilot(False)

    # Camera spectator
    spectator = world.get_spectator()
    cam_loc = spawn_point.location + carla.Location(z=30)
    spectator.set_transform(carla.Transform(cam_loc, carla.Rotation(pitch=-90)))

    # Attach RGB camera
    cam_bp = bp_lib.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", "800")
    cam_bp.set_attribute("image_size_y", "600")
    cam_bp.set_attribute("fov", "90")

    cam_transform = carla.Transform(carla.Location(x=0.6, z=1.6))
    camera = world.spawn_actor(cam_bp, cam_transform, attach_to=vehicle)

    frame_counter = {"id": 0}

    def process_image(image, vehicle):
        vel = vehicle.get_velocity()
        speed = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2) * 3.6
        frame_id = frame_counter["id"]
        filename = f"{images_folder}/frame_{frame_id:05d}_speed_{speed:.1f}.png"
        image.save_to_disk(filename)
        frame_counter["id"] += 1

    camera.listen(lambda img: process_image(img, vehicle))

    # -----------------------------------------------------
    # CSV LOG
    # -----------------------------------------------------
    csv_path = os.path.join(base_folder, "controls.csv")
    log_file = open(csv_path, "w", newline="")
    logger = csv.writer(log_file)
    logger.writerow(["time", "steer", "throttle", "brake", "speed_kmh", "driver_state"])

    # -----------------------------------------------------
    # MAIN SIMULATION LOOP
    # -----------------------------------------------------
    print(f"\nRunning Scenario {scenario_id} on {town_name}...")

    start = time.time()

    # Track critical behavior
    vehicle.driver_cancelled = False

    while time.time() - start < 20:
        t = time.time() - start

        # UPDATE SPECTATOR TO FOLLOW VEHICLE
        # vehicle_location = vehicle.get_transform().location
        # spectator_location = vehicle_location + carla.Location(z=30)
        # spectator.set_transform(carla.Transform(
        #     spectator_location, 
        #     carla.Rotation(pitch=-90)
        # ))

        # UPDATE SPECTATOR TO FOLLOW VEHICLE (behind view)
        vehicle_transform = vehicle.get_transform()
        vehicle_location = vehicle_transform.location
        vehicle_rotation = vehicle_transform.rotation

        # Position camera behind and above the vehicle
        spectator_location = vehicle_location - vehicle_transform.get_forward_vector() * 8 + carla.Location(z=3)
        spectator.set_transform(carla.Transform(
            spectator_location, 
            carla.Rotation(pitch=-15, yaw=vehicle_rotation.yaw)
        ))

        # Check keyboard
        driver_ok_pressed = keyboard.is_pressed("o")

        # Live dashboard message
        if driver_ok_pressed:
            vehicle.driver_cancelled = True
            if status_box is not None:
                try:
                    status_box.warning("🟠 Driver cancelled AI takeover — OK pressed")
                except:
                    pass

        if scenario_id == 1 or scenario_id == 2:
            if scenario_id == 1:
                steer, throttle, brake, speed = scenario_1_control(vehicle,t,driver_class,driver_ok_pressed)

            else:   # scenario 2
                steer, throttle, brake, speed = scenario_2_control(vehicle,t,driver_class,driver_ok_pressed, world)

            # Unified final state logic for both scenarios
            if driver_class == "critical drowsiness":
                if vehicle.driver_cancelled:
                    final_state = "critical_user_cancelled"
                else:
                    if hasattr(vehicle, "critical_start") and t - vehicle.critical_start > 5:
                        final_state = "critical_ai_takeover"
        elif scenario_id == 3:
            steer, throttle, brake, speed = scenario_3_control(vehicle, t)
        elif scenario_id == 4:
            steer, throttle, brake, speed = scenario_4_control(vehicle, t)
        elif scenario_id == 5:
            steer, throttle, brake, speed = scenario_5_control(vehicle, t, driver_ok_pressed, world)
            if vehicle.s5_resolved:
                final_state = "user_cancelled"
            elif hasattr(vehicle, "takeover_initial_speed"):
                final_state = "ai_takeover"
        elif scenario_id == 6:
            steer, throttle, brake, speed = scenario_6_control(vehicle, npc, t)
        else:
            raise ValueError("Scenario not implemented yet.")

        # Apply control
        vehicle.apply_control(
            carla.VehicleControl(
                steer=float(steer),
                throttle=float(throttle),
                brake=float(brake)
            )
        )

        logger.writerow([time.time(), steer, throttle, brake, speed, driver_class])
        world.tick()

    # -----------------------------------------------------
    # CLEANUP
    # -----------------------------------------------------
    print("\nCleaning up...")

    try:
        camera.stop()
    except:
        pass

    try:
        camera.destroy()
    except:
        pass

    try:
        vehicle.destroy()
    except:
        pass

    log_file.close()

    cleanup_after_scenario(world, client)

    # Allow OS time to release locks
    import gc
    gc.collect()
    time.sleep(0.5)

    # -----------------------------------------------------
    # FINAL RENAME
    # -----------------------------------------------------
    if scenario_id == 1 or scenario_id == 2 or scenario_id == 5:
        new_folder = f"output/Scenario{scenario_id}-{town_name}-{final_state.replace(' ', '_')}"

        if new_folder != base_folder:
            # remove destination if exists
            if os.path.exists(new_folder):
                shutil.rmtree(new_folder)

            try:
                os.rename(base_folder, new_folder)
                base_folder = new_folder
                print(f"Folder renamed → {new_folder}")
            except Exception as e:
                print("Rename error:", e)

    print(f"\nScenario {scenario_id} complete. Files saved in: {base_folder}\n")
    return base_folder

# ---------------------------------------------------------
# Cleanup After Scenario
# ---------------------------------------------------------
def cleanup_after_scenario(world, client):
    # turn off sync
    settings = world.get_settings()
    settings.synchronous_mode = False
    settings.fixed_delta_seconds = None
    world.apply_settings(settings)

    tm = client.get_trafficmanager()
    tm.set_synchronous_mode(False)

    # destroy all vehicles except traffic
    for a in world.get_actors().filter("vehicle.*"):
        try: a.destroy()
        except: pass

    # destroy every sensor
    for a in world.get_actors().filter("sensor.*"):
        try: a.destroy()
        except: pass

    import gc
    gc.collect()

    print("Cleanup finished.\n")