"""
display.py
----------
All OpenCV drawing/overlay helpers live here.
Keeps main.py clean and readable.
"""

import cv2


# ── Constants ────────────────────────────────────────────────────────────────
FONT = cv2.FONT_HERSHEY_SIMPLEX
OVERLAY_ALPHA = 0.55          # Transparency of the dark tip banner
FACE_BOX_THICKNESS = 2
TIP_BAR_HEIGHT = 90           # Height of the coaching tip banner (px)


def draw_face_box(frame, region: dict, color: tuple):
    """Draw a colored rectangle around the detected face."""
    x = region.get("x", 0)
    y = region.get("y", 0)
    w = region.get("w", 0)
    h = region.get("h", 0)

    if w > 0 and h > 0:
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, FACE_BOX_THICKNESS)


def draw_emotion_label(frame, label: str, region: dict, color: tuple):
    """Draw the emotion label just above the face bounding box."""
    x = region.get("x", 0)
    y = region.get("y", 0)

    # Make sure text doesn't go off-screen at the top
    text_y = max(y - 12, 20)
    cv2.putText(frame, label, (x, text_y), FONT, 0.75, color, 2, cv2.LINE_AA)


def draw_tip_banner(frame, tip: str, color: tuple):
    """
    Draw a semi-transparent dark banner at the bottom of the frame
    and render the coaching tip text on top of it.
    """
    h, w = frame.shape[:2]
    banner_y = h - TIP_BAR_HEIGHT

    # Create the dark overlay
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, banner_y), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, OVERLAY_ALPHA, frame, 1 - OVERLAY_ALPHA, 0, frame)

    # Header label
    cv2.putText(
        frame,
        "Interview Coach:",
        (12, banner_y + 26),
        FONT,
        0.55,
        color,
        1,
        cv2.LINE_AA,
    )

    # Wrap long tip text across two lines if needed
    lines = _wrap_text(tip, max_chars=68)
    for i, line in enumerate(lines[:2]):   # max 2 lines
        cv2.putText(
            frame,
            line,
            (12, banner_y + 52 + i * 26),
            FONT,
            0.52,
            (230, 230, 230),
            1,
            cv2.LINE_AA,
        )


def draw_quit_hint(frame):
    """Render a small 'Press Q to Quit' hint in the top-right corner."""
    h, w = frame.shape[:2]
    text = "Press Q to quit"
    (tw, _), _ = cv2.getTextSize(text, FONT, 0.45, 1)
    cv2.putText(
        frame,
        text,
        (w - tw - 10, 22),
        FONT,
        0.45,
        (180, 180, 180),
        1,
        cv2.LINE_AA,
    )


def draw_status(frame, message: str):
    """Show a centered status message (used while DeepFace loads or detects)."""
    h, w = frame.shape[:2]
    (tw, th), _ = cv2.getTextSize(message, FONT, 0.65, 2)
    x = (w - tw) // 2
    y = (h + th) // 2
    cv2.putText(frame, message, (x, y), FONT, 0.65, (80, 200, 255), 2, cv2.LINE_AA)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _wrap_text(text: str, max_chars: int) -> list:
    """Split text into lines of at most max_chars characters."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
