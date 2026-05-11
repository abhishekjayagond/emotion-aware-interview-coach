# 🎙️ Emotion-Aware Virtual Interview Coach

A beginner-friendly Python app that uses your **webcam**, **OpenCV**, and **DeepFace** to analyze your facial emotions in real time and give you instant interview coaching tips — right on screen.

---

## 📸 What It Does

| Detected Emotion | Coaching Tip Shown |
|------------------|--------------------|
| 😊 Happy         | Great energy! Keep that warm engagement. |
| 😐 Neutral       | Try adding a slight smile to appear more approachable. |
| 😢 Sad           | Sit up tall, recall a recent win to boost your mood. |
| 😠 Angry         | Relax your jaw, slow your breathing, stay calm. |
| 😨 Fearful       | Breathe deeply — you prepared for this! |
| 😲 Surprised     | Pause, think, then answer with confidence. |
| 🤢 Disgusted     | Keep expressions neutral — professionalism is key. |

---

## 🗂️ Project Structure

```
mini-project/
├── main.py              # Entry point — run this to start
├── emotion_detector.py  # DeepFace emotion analysis logic
├── coach.py             # Maps emotions → coaching tips & colors
├── display.py           # All OpenCV drawing / overlay helpers
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## ⚙️ Setup Instructions

### 1. Prerequisites

- Python **3.9 – 3.11** (DeepFace works best in this range)
- A working webcam
- Git (optional, for cloning)

### 2. Create a Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> ⏳ **First install may take a few minutes** — TensorFlow and DeepFace are large packages.

### 4. Run the App

```bash
python main.py
```

> 🔄 **The first run downloads DeepFace model weights** (~100 MB) automatically.  
> Subsequent runs start much faster.

### 5. Quit

Press **`Q`** on your keyboard (or close the window) to end the session.

---

## 🛠️ Tweaking the App

| What you want to change | Where to change it | Setting |
|-------------------------|--------------------|---------|
| Use a different webcam  | `main.py`          | `CAMERA_INDEX = 1` (or 2, etc.) |
| Speed vs. accuracy      | `main.py`          | `ANALYZE_EVERY_N` — lower = more frequent analysis (slower) |
| Add/edit coaching tips  | `coach.py`         | Edit the `COACHING_TIPS` dictionary |
| Change overlay colors   | `coach.py`         | Edit the `"color"` field (BGR tuples) |

---

## 🐛 Common Issues

### Webcam not opening
- Make sure no other app (Zoom, Teams, etc.) is using the webcam.
- Try changing `CAMERA_INDEX = 1` in `main.py`.

### `ModuleNotFoundError: No module named 'cv2'`
- Run `pip install opencv-python` inside your virtual environment.

### Very slow first frame
- Normal! DeepFace loads TensorFlow models on the first analysis. Subsequent frames are faster.

### Low accuracy in dim light
- Ensure your face is well-lit and centered in the frame.

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `opencv-python` | Webcam access & drawing overlays |
| `deepface` | Facial emotion recognition |
| `tensorflow` | Deep learning backend for DeepFace |
| `numpy` | Array operations |
| `Pillow` | Image utility (used internally by DeepFace) |

---

## 📄 License

MIT — free to use and modify for learning purposes.
