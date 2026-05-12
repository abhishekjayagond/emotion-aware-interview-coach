"""
coach.py
--------
Maps detected emotions to interview coaching tips.
Pure data/logic — no OpenCV or UI code here.
"""

# Coaching messages tailored to how each emotion affects interviews
# NOTE: Labels use plain ASCII only — cv2.putText cannot render emoji/Unicode
#       on Windows without a custom TTF font pipeline.
COACHING_TIPS = {
    "happy": {
        "label": "[HAPPY]",
        "tip": "Great energy! Maintain this warmth -- interviewers love engaged candidates.",
        "color": (0, 200, 80),    # green
    },
    "neutral": {
        "label": "[NEUTRAL]",
        "tip": "Good composure. Try adding a slight smile to appear more approachable.",
        "color": (200, 200, 0),   # yellow
    },
    "sad": {
        "label": "[SAD]",
        "tip": "You seem down. Take a breath, sit up tall, and recall a win to boost mood.",
        "color": (200, 80, 0),    # orange
    },
    "angry": {
        "label": "[ANGRY]",
        "tip": "Tension detected. Relax your jaw, slow your breathing, stay calm.",
        "color": (0, 0, 220),     # red (BGR)
    },
    "fear": {
        "label": "[FEARFUL]",
        "tip": "Nervousness is normal! Breathe deeply -- you prepared for this.",
        "color": (180, 0, 180),   # purple
    },
    "surprise": {
        "label": "[SURPRISED]",
        "tip": "Stay poised with unexpected questions. Pause, think, then answer.",
        "color": (220, 130, 0),   # orange-blue (BGR)
    },
    "disgust": {
        "label": "[DISGUSTED]",
        "tip": "Keep expressions neutral on tough topics -- professionalism is key.",
        "color": (0, 140, 180),   # teal
    },
    "unknown": {
        "label": "[DETECTING]",
        "tip": "Move closer to the camera or improve lighting.",
        "color": (150, 150, 150), # gray
    },
}


def get_coaching(emotion: str) -> dict:
    """
    Return coaching data for the given emotion string.

    Args:
        emotion: Emotion label returned by DeepFace (lowercase string).

    Returns:
        Dict with 'label', 'tip', and 'color' (BGR tuple).
    """
    return COACHING_TIPS.get(emotion.lower(), COACHING_TIPS["unknown"])
