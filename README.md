# 🚗 CARLA AI Assistant – Drowsiness-Aware Shared Control System

An AI-driven driver safety system that detects **driver drowsiness in real time** and intelligently decides **when to warn the driver and when to safely take control** — built using deep learning, explainable AI, and the CARLA autonomous driving simulator.

This project focuses on **human–AI collaboration**, not full autonomy: the driver remains in control unless safety is at risk.

---

## 👋 Why This Project Matters

Driver fatigue is one of the leading causes of road accidents. Most existing systems either:
- provide basic alerts, or  
- take full control away from the driver.

This project explores a better middle ground:  
**shared control**, where AI intervenes only when necessary and always allows the driver to override.

---

## 🧠 What We Built

**Driver Drowsiness Detection**
- Trained a custom CNN to classify driver alertness from facial images
- Used dlib’s **68-point facial landmarks** to extract meaningful features such as:
  - eye closure
  - mouth movement
  - pupil visibility
- Classifies the driver into four states:  
  *Alert, Slightly Drowsy, Very Drowsy, Critical*

**Explainable AI Reasoning**
- Integrated a **large language model (Mistral 7B)** to translate model outputs into
  clear, human-readable explanations
- Generates contextual voice feedback based on severity (e.g., time-bound warnings)

**Shared Control Driving Logic**
- Graduated alerts (soft → strong → autonomous action)
- Safe steering, braking, and speed control when the driver is unresponsive
- Driver override supported at all stages

**CARLA Simulation**
- Real-time vehicle actuation (steering, throttle, brake)
- Tested across **urban roads, highways, and emergency scenarios**
- Uses RGB camera and LiDAR emulation

---

## 🚦 Scenarios Tested

- City driving with progressive drowsiness alerts  
- Highway driving with safe shoulder stop  
- Lane drift and barrier avoidance  
- Wrong-lane entry detection  
- Red-light unresponsiveness  
- Emergency oncoming-vehicle evasion  

Each scenario validates both **AI decision-making** and **human override behavior**.

---

## 📊 Results at a Glance

- **97.9% validation accuracy** on drowsiness classification
- Consistent and explainable AI interventions
- Smooth collaboration between driver and AI
- Fully logged simulations (video, telemetry, AI reasoning, audio)

---

## 🖥️ Interactive Demo

A lightweight web interface allows users to:
- Upload a driver image
- Select a driving scenario
- Run a CARLA simulation
- Export videos, logs, and AI explanations

---

## 🧰 Tech Stack

- **Python**
- **PyTorch**
- **CNNs & Computer Vision**
- **dlib (Facial Landmarks)**
- **Mistral 7B (LLM)**
- **CARLA Simulator**
- **Web UI for control and monitoring**

---

## 🚀 Future Improvements

- Live video-based driver monitoring
- Multi-modal sensing (eye tracking, heart rate)
- Emotion-aware AI responses
- Reinforcement learning for personalized shared control
- Hardware-in-the-loop or real-world validation

---

## 👥 Contributors

- **Joshita Malla** – MS AI, Stony Brook University  
- **Bilal El Jamal** – PHD CE, Stony Brook University  

---

## 📬 Let’s Connect

If you’re interested in **AI safety, autonomous systems, or human–AI interaction**, feel free to explore the code or reach out.

