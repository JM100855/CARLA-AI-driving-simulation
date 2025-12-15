import streamlit as st
import os
import json
import pandas as pd
import carla
from llm_explanation import generate_explanation
from carla_simulation import run_scenario, start_carla, stop_carla, BASE_DIR
import subprocess


# =========================================================
# SCENARIO TITLES (Short)
# =========================================================
SCENARIO_TITLES = {
    1: "Urban Driving with Drowsiness Reactions",
    2: "Highway Driving with Drowsiness Reactions",
    3: "Approaching Barrier on Urban Street",
    4: "Switching into Wrong Lane on Two Way Road",
    5: "Driver Unresponsive at Red Light",
    6: "Oncoming Vehicle Approaching"
}

# =========================================================
# SCENARIO DESCRIPTIONS (Full PDF text)
# =========================================================
SCENARIO_DESCRIPTIONS = {
    1: "Critical state driver driving on an urban environment street without any danger any safety issue.",
    2: "Critical state driver driving on a highway without any danger any safety issue.",
    3: "Driving on an urban environment street and is about to hit a barrier.",
    4: "Driver switches lanes on a two way street.",
    5: "Driver unresponsive during red light.",
    6: "Vehicle is driving opposite to the car."
}

# =========================================================
# SCENARIO → TOWN Mapping
# =========================================================
SCENARIO_TOWN_MAP = {
    1: "Town01",
    2: "Town04",
    3: "Town01",
    4: "Town05",
    5: "Town05",
    6: "Town04"
}

# TOWN INFO for scenario 7 UI selection
TOWNS = {
    "Town01": "Town 01 is a small town with numerous T-junctions and a variety of buildings, surrounded by coniferous trees and featuring several small bridges spanning across a river.",
    "Town04": "Town 04 is a small mountain town surrounded by snow covered peaks and conifer trees. A multi lane highway loops around the map in a figure eight shape.",
    "Town05": "Town 05 is an urban environment set into a backdrop of conifer-covered hills with a raised highway and large multilane roads and junctions."
}

TOWN_IMAGES = {
    "Town01": "assets/images/towns/Town01.png",
    "Town04": "assets/images/towns/Town04.png",
    "Town05": "assets/images/towns/Town05.png"
}


# =========================================================
# STREAMLIT UI SETUP
# =========================================================
st.set_page_config(page_title="CARLA AI Drowsiness Monitor", layout="wide")
st.title("CARLA AI Drowsiness Monitor")

JSON_FOLDER = "assets/json"


# =========================================================
# STEP 1 — DRIVER IMAGE UPLOAD + ANALYSIS
# =========================================================
uploaded_image = st.file_uploader("Upload Driver Image", type=["png", "jpg", "jpeg"])

if uploaded_image is None and "driver_class" in st.session_state:
    st.session_state.clear()
    st.rerun()

if uploaded_image:
    st.image(uploaded_image, width=450)

    base_name = os.path.splitext(uploaded_image.name)[0]
    json_path = os.path.join(JSON_FOLDER, base_name + ".json")

    if not os.path.exists(json_path):
        st.error(f"No JSON found for {base_name}.json in assets/json")
        st.stop()

    with open(json_path, "r") as f:
        result_data = json.load(f)

    predicted_class = result_data["Predicted Class"].lower()

    status_colors = {
        "alert": "#2ecc71",
        "slightly drowsy": "#f1c40f",
        "very drowsy": "#e67e22",
        "critical drowsiness": "#e74c3c"
    }
    color = status_colors.get(predicted_class, "#2ecc71")

    st.header("AI Drowsiness Analysis")

    with st.spinner("Generating explanation..."):
        explanation = generate_explanation(result_data)

    st.markdown(
        f"""
        <div style='padding:18px; border-radius:10px;
            background-color:{color};
            color:#FFFFFF;
            margin-top:10px;
            font-size:16px;'>
            <strong>Driver State:</strong> {predicted_class.title()}
            <br>
            <strong>AI Suggestion:</strong> {explanation}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.session_state["driver_class"] = predicted_class


# =========================================================
# STEP 2 — SCENARIO SELECTION
# =========================================================
if "driver_class" in st.session_state:
    st.header("Simulation Scenarios")

    cols = st.columns(3)
    i = 0

    for sid, title in SCENARIO_TITLES.items():
        with cols[i]:
            st.markdown(
                f"""
                <div style='padding:15px; margin-bottom:15px; border-radius:12px;
                    background:rgba(0, 84, 163,0.5); border:1px solid transparent; color:white;'>
                    <h4 style='margin-bottom:5px;'>Scenario {sid}</h4>
                    <p style='font-size:15px;'>{title}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(f"Select Scenario {sid}", use_container_width=True):
                st.session_state["scenario_id"] = sid
                if "selected_town" in st.session_state:
                    del st.session_state["selected_town"]

        i = (i + 1) % 3


# =========================================================
# SHOW SELECTED SCENARIO + FULL DESCRIPTION
# =========================================================
if "scenario_id" in st.session_state:
    sid = st.session_state["scenario_id"]
    st.success(
        f"**Scenario {sid}:** {SCENARIO_TITLES[sid]}\n\n"
        f"**Description:** {SCENARIO_DESCRIPTIONS[sid]}"
    )


# =========================================================
# STEP 3 — TOWN DISPLAY + DESCRIPTION
# =========================================================
scenario_id = st.session_state.get("scenario_id", None)

# Auto select town for scenarios 1 to 6
if scenario_id in SCENARIO_TOWN_MAP and SCENARIO_TOWN_MAP[scenario_id] is not None:
    auto_town = SCENARIO_TOWN_MAP[scenario_id]
    st.session_state["selected_town"] = auto_town
    # Fetch town description
    town_description = TOWNS.get(auto_town, "No description available.")
    # Show message
    st.info(
        f"Environment set to **{auto_town}** for **Scenario {scenario_id}**\n\n"
        f"**Town Description:** {town_description}"
    )
    # Show full width town image
    if auto_town in TOWN_IMAGES:
        st.image(TOWN_IMAGES[auto_town], use_container_width=True)


# =========================================================
# STEP 4 — RUN SIMULATION
# =========================================================
if "selected_town" in st.session_state and "scenario_id" in st.session_state:
    if st.button("🚗 Run CARLA Simulation", use_container_width=True):

        scenario = st.session_state["scenario_id"]
        town = st.session_state["selected_town"]
        driver_class = st.session_state["driver_class"]

        st.write(f"Starting CARLA for Scenario {scenario} in {town}...")

        # Placeholder status box for real-time updates
        status_box = st.empty()

        # TEMPORARY placeholder output (final is assigned after sim)
        temp_folder = os.path.join(BASE_DIR, "output", "temp_running_folder")
        st.session_state["output_path"] = temp_folder

        carla_process = start_carla()
        st.write("CARLA launched. Connecting to server...")
        is_error = False

        try:
            client = carla.Client("localhost", 2000)
            client.set_timeout(60.0)

            st.write("Connection successful. Running scenario now...")
            final_folder = run_scenario(client, town, scenario, driver_class, status_box)

            # SAVE THE REAL FINAL FOLDER
            st.session_state["output_path"] = os.path.join(BASE_DIR, final_folder)

        except Exception as e:
            is_error = True
            st.error(f"**Simulation Error:** {str(e)}")

        finally:
            if not is_error:
                st.success("Simulation Completed!")
            st.write("Shutting down CARLA simulator...")
            stop_carla(carla_process)
            st.write("CARLA stopped successfully.")


# =========================================================
# STEP 5 — VIEW OUTPUT
# =========================================================
if "output_path" in st.session_state:
    st.header("Simulation Log and Output")

    output_dir = os.path.abspath(st.session_state["output_path"])

    csv_path = os.path.join(output_dir, "controls.csv")

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns([1, 1])

        with col1:
            st.download_button(
                "⬇️ Download CSV",
                data=df.to_csv(index=False),
                file_name="controls.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            if st.button("📂 Open Folder", use_container_width=True):
                try:
                    subprocess.Popen(f'explorer "{output_dir}"')
                except Exception as e:
                    st.error(f"Failed to open folder: {e}")

    else:
        st.warning("CSV file not found.")