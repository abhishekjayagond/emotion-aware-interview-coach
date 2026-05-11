"""
main.py
-------
Emotion-Aware Virtual Interview Coach
======================================
Entry point. Ties together webcam capture, emotion detection,
coaching tips, and the OpenCV display.

Run:
    python main.py

Press Q (or close the window) to quit.
"""

import cv2

from emotion_detector import analyze_emotion
from coach import get_coaching
from display import (
    draw_face_box,
    draw_emotion_label,
    draw_tip_banner,
    draw_quit_hint,
    draw_status,
)


# ── Configuration ─────────────────────────────────────────────────────────────
WINDOW_TITLE   = "Emotion-Aware Interview Coach"
ANALYZE_EVERY_N = 5   # Run DeepFace every N frames to keep the feed smooth

# Camera indices to test in order (0 = built-in webcam on most laptops)
CAMERA_CANDIDATES = [0, 1, 2]


# ── Webcam Helper ─────────────────────────────────────────────────────────────
def open_webcam():
    """
    Try to open a working webcam on Windows.

    Uses the DirectShow (CAP_DSHOW) backend, which is the most reliable
    choice on Windows and avoids the common "camera index out of range" error.

    Returns:
        cv2.VideoCapture if a working camera is found, or None if all fail.
    """
    for index in CAMERA_CANDIDATES:
        print(f"[INFO] Trying camera index {index} with DirectShow backend...")

        # CAP_DSHOW is the Windows-native capture backend — much more reliable
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

        if not cap.isOpened():
            print(f"[WARN] Camera index {index} could not be opened. Trying next...")
            cap.release()
            continue

        # Opening alone isn't enough — take a test frame to confirm it streams
        ret, _ = cap.read()
        if not ret:
            print(f"[WARN] Camera index {index} opened but couldn't read a frame. Trying next...")
            cap.release()
            continue

        print(f"[INFO] Camera index {index} is working. ✓")
        return cap

    # All candidates failed
    print("[ERROR] No working webcam found after trying indices:", CAMERA_CANDIDATES)
    print("        Make sure your webcam is connected and not in use by another app.")
    return None


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Open webcam with automatic Windows-friendly fallback detection
    cap = open_webcam()
    if cap is None:
        return  # open_webcam() already printed the error details

    print("[INFO] Webcam started. Press Q to quit.")
    print("[INFO] DeepFace will warm up on the first few frames — this is normal.\n")

    frame_count = 0

    # Store the last successful analysis so we can display it between analyses
    last_result = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read frame from webcam (camera may have disconnected).")
            break

        frame_count += 1

        # ── Run emotion analysis every N frames ───────────────────────────────
        if frame_count % ANALYZE_EVERY_N == 0:
            result = analyze_emotion(frame)
            if result is not None:
                last_result = result

        # ── Draw overlays ─────────────────────────────────────────────────────
        if last_result:
            emotion  = last_result["emotion"]
            region   = last_result["region"]
            coaching = get_coaching(emotion)
            color    = coaching["color"]

            draw_face_box(frame, region, color)
            draw_emotion_label(frame, coaching["label"], region, color)
            draw_tip_banner(frame, coaching["tip"], color)
        else:
            # No face detected yet — show a friendly prompt
            draw_status(frame, "Looking for your face...")

        draw_quit_hint(frame)

        # ── Show frame ────────────────────────────────────────────────────────
        cv2.imshow(WINDOW_TITLE, frame)

        # Quit on 'q' or 'Q' key, or window close button
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q")):
            break

    # ── Cleanup ───────────────────────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Session ended. Good luck with your interview! 🎯")


if __name__ == "__main__":
    main()
