# Emotion-Aware Interview Coach

An interactive Python-based mock interview platform that uses computer vision to analyze facial expressions and adapt interview questions in real time. It features a responsive local web interface, tracking metrics like composure stability, simulated speaking pace, and virtual eye contact to generate a detailed performance evaluation report at the end of the session.

## Features

- **Adaptive Interview Flow**: Progresses through 5 standard interview stages (Intro, Technical, Behavioral, Situational, and Wrap-up). Question difficulty adjusts dynamically based on the candidate's detected emotional state.
- **Real-Time Emotion Tracking**: Integrates DeepFace to recognize 7 facial emotions (happy, neutral, sad, angry, fear, surprise, disgust) with temporal smoothing and suppression thresholds to eliminate detection noise.
- **Composure scorecard**: Computes a live composure percentage based on facial cues, showing a real-time stability graph.
- **Eye Contact Estimation**: Proxies eye contact by measuring face alignment stability and detection consistency across frames.
- **Simulated Speech Metrics**: Algorithmic estimation of speaking pace (WPM), response time, and filler words (um, uh, like) based on session timing heuristics.
- **Web UI & Control Panel**: A local multi-threaded HTTP server displaying a desktop dashboard. Includes Next, Previous, Restart, and Finish navigation.
- **Pause & Resume States**: Allows candidates to pause the interview. Pausing suspends video processing, freezes response clocks, and offsets the session logger to ensure accurate duration metrics.
- **Keyboard Hotkeys**: Hands-free keyboard shortcuts (Space to Pause, Left/Right Arrows to navigate, Q to Finish/Exit, R/Enter to Restart).
- **Post-Session Evaluation Report**: Generates a performance analysis view showing an overall score, communication breakdown, strengths, areas of focus, interactive composure timeline, and a personalized improvement roadmap.
- **Synthetic Demo Mode**: Includes an animated fallback mode to simulate interview state transitions without requiring a physical camera.

## Tech Stack

- **Python**: Core logic, states, and telemetry.
- **OpenCV & Pillow**: BGR video stream acquisition, frame transformation, and compression.
- **DeepFace (TensorFlow/Keras Backend)**: Convolutional neural network classification for facial coordinates and emotion scores.
- **HTML5 / CSS3 / JavaScript**: Desktop interface, absolute overlays, CSS video filters, and SVG data graphics.
- **Server-Sent Events (SSE)**: Zero-dependency HTTP streaming pushing state payloads to the browser.
- **Matplotlib**: Post-session static graph compiler (saved locally on exit).

## Project Structure

- `main.py`: Entry point that boots the background web server, processes input video streams, runs deepface analysis, and runs the interview manager state loop.
- `web_server.py`: Multi-threaded local server serving static files, MJPEG video buffers, SSE broadcasts, and REST callbacks.
- `emotion_detector.py`: DeepFace integration wrapper with rolling-average smoothing and minimum confidence filters.
- `coach.py`: Coaching mapping file linking specific emotions to actionable advice.
- `interview_questions.py`: Data bank containing stage-specific questions and follow-up prompts.
- `session_logger.py`: Telemetry logger recording session metrics, exporting them to timestamped CSV sheets, and managing pause offsets.
- `session_summary.py`: Calculations for the final JSON summary payloads and local Matplotlib PNG graph exports.
- `webcam_handler.py`: Source manager parsing webcams, mp4 files, and generating the synthetic animated avatar demo.
- `web/`: Front-end single-page application:
  - `index.html`: Desktop dashboard structure and evaluation report overlays.
  - `style.css`: Design system stylesheet defining the bright light theme, Inter font variables, 8px layout grid, and transitions.
  - `app.js`: Event listeners, keyboard shortcuts, SVG coordinate drawing, and SSE connections.

## Installation

### 1. Prerequisites
Ensure you have Python 3.9+ installed on your system.

### 2. Setup Repository and Environment
Clone the repository and set up a Python virtual environment:

```bash
# Clone the repository
git clone https://github.com/abhishekjayagond/emotion-aware-interview-coach.git
cd emotion-aware-interview-coach

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (CMD):
.\venv\Scripts\activate.bat
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Launching the Session
To start the program using your default webcam:
```bash
python main.py
```

To run in **Demo Mode** (uses an animated placeholder face instead of the camera, ideal for testing):
```bash
python main.py --demo
```

Upon launching, the console will start the local server and automatically open your default browser to `http://localhost:8000/`.

### 2. Interactive Controls
- **Calibrating**: The browser displays a loading overlay until a face is detected.
- **Pause / Resume**: Press the `Spacebar` or click the **Pause** button to freeze the interview. The video feed will blur and dim.
- **Navigate**: Press the `ArrowRight` (Next) or `ArrowLeft` (Previous) keys to navigate between questions.
- **Finish**: Press `Q` or click **Finish Session** to stop tracking and show the summary report.
- **Reset**: From the report page, press `Enter` or click **Practice Again** to restart.
- **Quit**: Press `Q` or click **Quit Application** to shut down the Python process and close connections.

## Screenshots

Static dashboards and summary evaluations are logged directly in the session folders.

| Interview Workspace | Performance Report |
|:---:|:---:|
| ![HUD Placeholder](assets/screenshots/hud_placeholder.png) | ![Summary Placeholder](assets/screenshots/summary_placeholder.png) |

## Current Capabilities

- **Local Execution**: All facial profiling and web serving runs locally on your machine with no external network calls.
- **Adaptive Content**: Dynamically responds to fear or sadness by serving calming questions, while maintaining high technical difficulty if neutral or happy.
- **Simulated Performance Analytics**: Evaluates response timing patterns and composure stability to compute convincing feedback metrics without the need for heavy speech-to-text processing.

## Future Improvements

- **Audio Speech-to-Text**: Incorporate local whisper transcription models to analyze actual spoken communication and provide syntax evaluations.
- **LLM Question Generators**: Integrate small local language models (such as LLaMA or Phi) to parse uploaded resume text files and generate mock interview questions dynamically.
- **Comparative Session Analytics**: Build a local database to store performance over time and graph mock interview progress across multiple sessions.
