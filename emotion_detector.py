"""
emotion_detector.py
-------------------
Handles face detection and emotion analysis using DeepFace.
Keeps detection isolated so it's easy to swap models later.
"""

from deepface import DeepFace


def analyze_emotion(frame):
    """
    Analyze the dominant emotion in a given video frame.

    Args:
        frame: A BGR image frame from OpenCV.

    Returns:
        A dict with keys:
            - 'emotion'  : str  — dominant emotion label (e.g. "happy")
            - 'scores'   : dict — all emotion scores (0-100)
            - 'region'   : dict — face bounding box (x, y, w, h)
        Returns None if no face is detected or analysis fails.
    """
    try:
        # enforce_detection=False prevents errors when no face is found
        results = DeepFace.analyze(
            img_path=frame,
            actions=["emotion"],
            enforce_detection=False,
            silent=True,
        )

        # DeepFace returns a list; pick the first (most prominent) face
        if not results:
            return None

        face_data = results[0]

        dominant_emotion = face_data.get("dominant_emotion", "unknown")
        emotion_scores = face_data.get("emotion", {})
        region = face_data.get("region", {"x": 0, "y": 0, "w": 0, "h": 0})

        return {
            "emotion": dominant_emotion,
            "scores": emotion_scores,
            "region": region,
        }

    except Exception as e:
        # Silently skip bad frames (blur, poor lighting, etc.)
        print(f"[Detector] Skipped frame: {e}")
        return None
