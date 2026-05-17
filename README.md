# Emotion-Aware Interview Coach

A modular, real-time AI interview simulator built with Python, OpenCV, and DeepFace. It transforms a standard webcam feed into an immersive, analytic interview environment, combining facial emotion recognition with dynamic conversational flow.

![Demo Placeholder](assets/demo/demo_placeholder.gif)

## 📌 Project Overview

This project was built to explore real-time computer vision and state-machine-driven UI within a single cohesive application. Instead of acting as a passive dashboard, it acts as an active coaching system: it asks questions, listens, analyzes facial expressions, and adjusts the interview difficulty based on your emotional composure.

**Important Note:** To keep this project lightweight and offline-friendly, it relies entirely on visual analysis and timing heuristics. It does *not* use a Large Language Model (LLM) backend for dynamic speech generation, nor does it perform actual audio transcription.

## ✨ Key Features

- **Adaptive Conversational Engine**: Progresses naturally through interview stages (Intro, Technical, Behavioral, Situational) and adjusts question difficulty based on the candidate's detected nervousness or stability.
- **Real-Time Emotion Tracking**: Uses `DeepFace` to analyze facial expressions, bolstered by custom temporal smoothing and minimum-size thresholds to eliminate background noise and flickering.
- **Cinematic Glassmorphism UI**: High-density overlays rendered directly on the OpenCV frame using Pillow (PIL) for beautiful anti-aliased typography and rounded translucent panels.
- **Simulated Communication Metrics**: Tracks "speaking pace" and "filler words" through clever heuristics tied to the interview state machine, providing a realistic coaching feel without heavy audio processing dependencies.
- **Session Analytics Summary**: Upon ending the interview, generates a beautiful product-style summary overlay detailing overall composure, pace, and dominant emotions.

## 🏗️ Architecture

The application is built completely modularly:
- `main.py`: The core state machine managing interview stages, delays, and overlay injection.
- `display.py`: Handles all UI rendering, using a custom anti-aliased Pillow-to-OpenCV masking technique for floating glassmorphism panels.
- `emotion_detector.py`: Wraps the DeepFace model with a rolling-average smoothing algorithm and bounding-box validation.
- `interview_questions.py`: Provides the dynamic, emotion-responsive question pool.
- `session_logger.py` & `session_summary.py`: Manage data serialization to CSV and Matplotlib trend generation.

## 🚀 Setup & Usage

### 1. Requirements
Ensure you have Python 3.9+ installed.

```bash
# Clone the repository
git clone https://github.com/yourusername/emotion-aware-interview-coach.git
cd emotion-aware-interview-coach

# Set up a virtual environment (recommended)
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Simulator

To start an interview session using your primary webcam:
```bash
python main.py
```

To run it in **Demo Mode** (forces an animated avatar instead of the webcam, perfect for testing):
```bash
python main.py --demo
```

To analyze a pre-recorded video:
```bash
python main.py --source my_interview.mp4
```

## 📸 Screenshots

*(Placeholders for future screenshots)*

| Dashboard HUD | Session Summary |
|:---:|:---:|
| ![HUD Placeholder](assets/screenshots/hud_placeholder.png) | ![Summary Placeholder](assets/screenshots/summary_placeholder.png) |

## ⚠️ Limitations & Honesty

- **Heuristic Audio Metrics**: The "Pace" and "Filler Words" trackers are algorithmic heuristics designed to enhance the *feel* of the coaching environment. They do not process real audio.
- **DeepFace Dependency**: Emotion detection relies heavily on lighting and face angle. Strong backlighting or extreme angles will degrade detection confidence.
- **Hardware Requirements**: DeepFace is somewhat computationally expensive. While the app limits analysis to every Nth frame, it still requires a modern multi-core CPU or basic GPU for a smooth 30fps experience.

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
