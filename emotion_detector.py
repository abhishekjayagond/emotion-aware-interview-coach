"""
emotion_detector.py
-------------------
Handles face detection and emotion analysis using DeepFace.
Features robust temporal smoothing, cooldowns, and size thresholds 
to prevent flickering and unrealistic detections from backgrounds.
"""

from collections import deque
from deepface import DeepFace

# Store recent score dictionaries for temporal smoothing
_score_history = deque(maxlen=8)
_last_emotion = "neutral"
_frames_since_change = 0

def analyze_emotion(frame):
    """
    Analyze the dominant emotion in a given video frame.

    Args:
        frame: A BGR image frame from OpenCV.

    Returns:
        A dict with keys:
            - 'emotion'  : str  — dominant emotion label
            - 'scores'   : dict — all emotion scores (0-100)
            - 'region'   : dict — face bounding box (x, y, w, h)
        Returns None if no face is detected, face is too small, or analysis fails.
    """
    global _last_emotion, _frames_since_change
    try:
        # enforce_detection=False prevents errors when no face is found,
        # but we handle minimum confidence and size manually below.
        results = DeepFace.analyze(
            img_path=frame,
            actions=["emotion"],
            enforce_detection=False,
            silent=True,
        )

        if not results:
            return None

        face_data = results[0]
        region = face_data.get("region", {"x": 0, "y": 0, "w": 0, "h": 0})

        # 1. Minimum Face-Size Threshold 
        # (Ignore tiny detections that are usually background noise)
        if region["w"] < 50 or region["h"] < 50:
            return None

        emotion_scores = face_data.get("emotion", {})

        # 2. Temporal Smoothing (Rolling Average over 8 frames)
        _score_history.append(emotion_scores)
        
        avg_scores = {}
        for key in _score_history[0].keys():
            avg_scores[key] = sum(s.get(key, 0) for s in _score_history) / len(_score_history)
            
        dominant_emotion = max(avg_scores, key=avg_scores.get)
        
        # 3. Low-Confidence Suppression
        # If no emotion is clearly dominant, default to neutral
        if avg_scores[dominant_emotion] < 35.0:
            dominant_emotion = "neutral"

        # 4. Emotion Switching Cooldown
        # Prevent rapid flickering by requiring an emotion to stick around
        _frames_since_change += 1
        if dominant_emotion != _last_emotion:
            # Require at least 5 frames before allowing a switch
            if _frames_since_change < 5:
                dominant_emotion = _last_emotion
            else:
                _last_emotion = dominant_emotion
                _frames_since_change = 0

        return {
            "emotion": dominant_emotion,
            "scores": avg_scores,
            "region": region,
        }

    except Exception:
        # Silently skip bad frames (blur, poor lighting, etc.)
        return None
