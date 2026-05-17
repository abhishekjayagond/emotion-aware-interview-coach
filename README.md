# Emotion-Aware Interview Coach

A Python-based interview practice tool built with OpenCV and DeepFace. It uses a webcam feed to analyze facial expressions and simulate a real-time interview environment, tracking composure and adapting questions based on how nervous or relaxed you appear.

![Demo](assets/demo/demo_placeholder.gif)

## Project Overview

I built this project to explore real-time computer vision and state-machine-driven UI. Instead of just displaying raw webcam data, it acts as an interactive interviewer: it asks questions, tracks facial expressions, and adjusts the difficulty of follow-up questions based on emotional stability.

**Note:** This project is designed to run locally and lightweight. It relies on visual heuristics and timing rather than LLMs for speech generation, and it doesn't process actual audio.

## Key Features

- **Adaptive Interview Flow**: Progresses through standard interview stages (Intro, Technical, Behavioral, Situational). The questions get easier if it detects nervousness, and stay challenging if you appear calm.
- **Emotion Tracking**: Uses `DeepFace` to read expressions. I added rolling-average smoothing and size thresholds to reduce jitter and ignore background noise.
- **Custom OpenCV UI**: Built a clean interface drawn directly onto the video frames using Pillow (PIL) for better typography and translucent rounded panels.
- **Simulated Speech Metrics**: Uses state machine timing to estimate metrics like speaking pace and filler words, giving the feel of a full communication analysis without heavy audio dependencies.
- **Session Summary**: Generates a quick performance breakdown (composure score, pace, dominant emotions) when you end the session.

## Architecture

The codebase is organized into modular components:
- `main.py`: The main loop and state machine handling interview stages and overlay timing.
- `display.py`: All UI rendering logic, including the Pillow-to-OpenCV masking for the UI panels.
- `emotion_detector.py`: DeepFace integration with custom temporal smoothing to prevent flickering.
- `interview_questions.py`: The question bank and logic for picking questions based on current emotion.
- `session_logger.py` & `session_summary.py`: Handles CSV logging and Matplotlib graph generation.

## Setup & Usage

### 1. Requirements
You'll need Python 3.9+ installed.

```bash
# Clone the repository
git clone https://github.com/yourusername/emotion-aware-interview-coach.git
cd emotion-aware-interview-coach

# Set up a virtual environment
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the App

To start an interview session using your default webcam:
```bash
python main.py
```

To run it in **Demo Mode** (uses an animated avatar instead of the webcam, useful for testing the UI):
```bash
python main.py --demo
```

To analyze a pre-recorded video:
```bash
python main.py --source my_interview.mp4
```

Press `Q` during the session to view your summary, and `Q` again to exit.

## Screenshots

*(Placeholders for future screenshots)*

| Dashboard | Session Summary |
|:---:|:---:|
| ![HUD Placeholder](assets/screenshots/hud_placeholder.png) | ![Summary Placeholder](assets/screenshots/summary_placeholder.png) |

## Limitations

- **Simulated Audio Metrics**: The "Pace" and "Filler Words" trackers are algorithmic estimates based on timing, not actual audio transcription.
- **Detection Accuracy**: DeepFace relies on decent lighting and clear camera angles. Strong backlighting will drop the detection confidence.
- **Performance**: DeepFace inference takes CPU/GPU resources. The app limits analysis to every 5th frame to maintain ~30fps on standard machines, but a modern CPU or basic GPU is recommended.

## License
MIT License
