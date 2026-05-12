# Emotion-Aware Virtual Interview Coach

A Python desktop app that reads your webcam feed, detects your facial expression using DeepFace, and shows you real-time coaching tips on screen based on what it sees. Built as a college mini-project to explore computer vision and practical machine learning.

No server. No cloud API. Everything runs locally.

---

## What It Actually Does

The app opens your webcam (or a video/image file), runs facial emotion analysis every few frames, and overlays:

- A **face bounding box** coloured by the detected emotion
- An **emotion label** and **confidence percentage**
- A **coaching tip** relevant to that emotion in an interview context
- A **live analytics sidebar** showing session duration, dominant emotion, average confidence, and per-emotion frequency
- A **rotating interview question** to practise answering while the analysis runs
- A **dot-based emotion timeline** at the top that builds up over the session

When you quit, it:
- Prints a session summary to the terminal
- Saves a **CSV log** of every reading (timestamp, emotion, confidence, all scores)
- Generates a **Matplotlib graph** (PNG) with a timeline, frequency chart, and confidence breakdown

**What it does not do:** It does not evaluate your answers, track eye contact, or produce any kind of objective interview score. It is a practice aid, not a grading tool.

---

## Demo

> _Add a screenshot or GIF here once you have one._
>
> Suggested: a screen recording of the overlay window during a short session, followed by the generated graph PNG.

```
[screenshot placeholder - webcam_overlay.png]
[screenshot placeholder - emotion_graph_sample.png]
```

---

## Honest Notes on Accuracy

DeepFace is a solid open-source library, but facial emotion detection is hard and imperfect.

A few things to keep in mind:

- **It estimates, it does not read minds.** The model looks at facial muscle positions. A blank resting face often reads as "sad" or "neutral" even when you feel fine.
- **Lighting matters a lot.** Dim or side-lit environments produce unreliable results. Face a window or a desk lamp.
- **Fast head movements confuse it.** Hold a natural, steady posture for better readings.
- **Confidence percentages are relative scores**, not probabilities. A 70% "happy" score just means the model weighted happiness highest out of the seven categories -- not that it is 70% sure.
- The model runs every 5 frames by default to keep the feed smooth. You can lower this number to analyse more frequently at the cost of frame rate.

Use the feedback as a rough mirror, not a verdict.

---

## Features

- Real-time emotion detection via [DeepFace](https://github.com/serengil/deepface)
- Coaching tips mapped to 7 emotions: happy, neutral, sad, angry, fearful, surprised, disgusted
- Live analytics sidebar: dominant emotion, average confidence, breakdown by emotion
- Dot-based emotion timeline showing how your expression changed over the session
- Rotating pool of 40 interview questions across 4 categories (Behavioural, Technical, Situational, Career)
- Session CSV log saved automatically on exit
- Matplotlib summary graph (PNG) with three panels: timeline, frequency, and avg confidence
- **Multiple input modes:** live webcam, pre-recorded video file, static image, or demo mode (no camera needed)
- Automatic webcam detection with a per-index timeout -- no indefinite hanging if no camera is found
- Demo mode generates a synthetic animated face so you can explore the interface without a camera

---

## Project Structure

```
mini-project/
|
|-- main.py                # Entry point + CLI argument parser
|-- emotion_detector.py    # DeepFace wrapper (analyze_emotion)
|-- coach.py               # Emotion -> coaching tip + colour mapping
|-- display.py             # All OpenCV drawing helpers (layout, overlays)
|-- webcam_handler.py      # Source detection: webcam / video / image / demo
|-- session_logger.py      # In-memory history + CSV export
|-- session_summary.py     # Console summary + Matplotlib graph generation
|-- interview_questions.py # Question bank (40 questions, 4 categories)
|-- requirements.txt       # Python dependencies
|-- README.md              # This file
|
`-- session_logs/          # Created automatically on first run
    |-- session_YYYYMMDD_HHMMSS.csv
    `-- emotion_graph_YYYYMMDD_HHMMSS.png
```

---

## How It Works (Brief Architecture)

```
Webcam / Video / Image / Demo
          |
          v
   webcam_handler.py        <-- detects and opens the source
          |
          v
   emotion_detector.py      <-- runs DeepFace every N frames
          |
          +--------> session_logger.py   <-- records each reading in memory
          |
          v
      coach.py              <-- maps emotion string to tip + colour
          |
          v
      display.py            <-- draws all overlays onto the frame
          |
          v
   cv2.imshow()             <-- shows the annotated frame in a window

  On quit:
   session_logger.save_csv()     --> session_logs/*.csv
   session_summary.save_graph()  --> session_logs/*.png
```

Each concern is in its own file. You can swap out the emotion model, change the coaching tips, or redesign the overlay without touching anything else.

---

## Setup

### Requirements

- Python 3.9 to 3.11 (DeepFace + TensorFlow have limited compatibility outside this range)
- A webcam is optional -- the app falls back to demo mode automatically
- Windows, macOS, or Linux should all work; the DirectShow webcam backend is only used on Windows

### 1. Clone or download the project

```bash
git clone https://github.com/your-username/mini-project.git
cd mini-project
```

### 2. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs OpenCV, DeepFace, TensorFlow, Matplotlib, and a few smaller packages. The first install takes a few minutes because TensorFlow is large.

### 4. First run

```bash
python main.py
```

On the very first run, DeepFace downloads its model weights (around 100 MB total). This only happens once; subsequent runs start in a few seconds.

---

## Running the App

```bash
# Auto-detect webcam; fall back to demo mode if none found
python main.py

# Force demo mode (no camera required at all)
python main.py --demo

# Analyse a pre-recorded video file
python main.py --source path/to/video.mp4

# Analyse a static image (press Q when done)
python main.py --source path/to/photo.jpg

# Use a specific camera index (e.g. an external USB webcam)
python main.py --source 1

# Give the webcam detector more time per index (default is 4 seconds)
python main.py --timeout 8

# Exit with an error if no camera is found instead of using demo mode
python main.py --no-fallback

# Help
python main.py --help
```

Press **Q** to end the session. The summary and output files are generated on exit.

---

## Supported Input Modes

| Mode | How to use | Notes |
|------|-----------|-------|
| Live webcam | `python main.py` | Tries indices 0, 1, 2 with a 4-second timeout each |
| Demo mode | `--demo` | Animated synthetic face; useful for testing the UI |
| Video file | `--source file.mp4` | Supports `.mp4 .avi .mov .mkv .wmv .flv .m4v` |
| Image file | `--source photo.jpg` | Supports `.jpg .jpeg .png .bmp .webp .tiff` |
| Specific camera index | `--source 1` | Pass the index as a number string |

---

## Configuration

Most things you might want to change are constants at the top of `main.py`:

| Constant | Default | Effect |
|----------|---------|--------|
| `ANALYZE_EVERY_N` | `5` | Run DeepFace every N frames. Lower = more frequent, higher CPU usage |
| `QUESTION_CHANGE_N` | `150` | Rotate the interview question every N frames (~5 s at 30 fps) |
| `LOG_DIR` | `"session_logs"` | Folder where CSV and PNG outputs are saved |

Coaching tips and colours live in `coach.py` in the `COACHING_TIPS` dictionary. Each entry has a `label`, `tip`, and `color` (BGR tuple). Edit freely.

---

## Output Files

Every session produces two files in `session_logs/`:

**CSV log** (`session_YYYYMMDD_HHMMSS.csv`):

| Column | Description |
|--------|-------------|
| `timestamp` | Wall-clock time of the reading |
| `emotion` | Detected dominant emotion |
| `confidence_pct` | Score of the dominant emotion (0-100) |
| `all_scores_json` | Full score dict for all 7 emotions |

**Graph PNG** (`emotion_graph_YYYYMMDD_HHMMSS.png`):

Three panels:
1. Emotion timeline -- dot per reading, colour = emotion, size = confidence
2. Frequency bar chart -- how often each emotion appeared
3. Horizontal bars -- average confidence per emotion

---

## Known Limitations

- **Emotion detection is not reliable in low light.** If the room is dim, expect a lot of "neutral" or "sad" readings regardless of how you actually feel.
- **The model struggles with glasses and face coverings.** Partial occlusion throws off the landmark detection.
- **Demo mode is not realistic.** The synthetic face is a coloured circle -- DeepFace will detect something, but readings will be erratic. It is there for UI testing, not practice.
- **Video file analysis plays at the original frame rate** but DeepFace only runs every 5 frames, so fast sections of a video may get fewer readings.
- **Session duration in the summary is wall-clock time**, not actual video time. If you pause or the detector is slow, the duration reflects that.
- **TensorFlow startup is slow.** The first annotated frame always takes a few extra seconds. This is normal.
- The app is a single-window desktop tool. There is no web interface, no dashboard, no real-time sharing.

---

## Future Improvements

Things that would genuinely make this better (not just features for the sake of it):

- [ ] Replace DeepFace with a lighter model (MediaPipe or a custom-trained MobileNet) for faster inference
- [ ] Add posture detection via pose landmarks to catch slouching or leaning
- [ ] Track eye contact by estimating gaze direction
- [ ] Record a short video clip of the session alongside the graph
- [ ] Show a scrollable full session replay after quitting
- [ ] Let the user select a question category to focus on
- [ ] Export the summary as a PDF report

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `opencv-python` | >= 4.8 | Webcam capture and all drawing operations |
| `deepface` | >= 0.0.93 | Facial emotion recognition |
| `tensorflow` | >= 2.13 | Neural network backend for DeepFace |
| `tf-keras` | >= 2.16 | Keras compatibility layer |
| `numpy` | >= 1.24 | Array handling |
| `Pillow` | >= 10.0 | Image utilities (used internally by DeepFace) |
| `matplotlib` | >= 3.8 | Post-session graph generation |

---

## Troubleshooting

**Webcam not detected**
The app tries camera indices 0, 1, and 2 with a 4-second timeout per index. If all fail, it drops into demo mode. If you want to force a specific index, use `--source 0` (or 1, or 2). Make sure no other app (Zoom, Teams, OBS) has the camera locked.

**Very slow first frame**
Normal. TensorFlow loads model weights on the first inference call. Subsequent frames are much faster.

**`ModuleNotFoundError`**
Make sure your virtual environment is activated before running. Run `pip install -r requirements.txt` again if a module is missing.

**Low or erratic confidence scores**
Check your lighting. Sit directly facing a light source if possible. Avoid strong backlight (e.g. a bright window behind you).

**`UnicodeEncodeError` in the terminal**
The terminal output uses ASCII only. If you see this error, it likely came from a `print()` call in a dependency, not this project. Try running in Windows Terminal instead of the default Command Prompt.

---

## License

MIT. Use it, break it, learn from it. Attribution is appreciated but not required.
