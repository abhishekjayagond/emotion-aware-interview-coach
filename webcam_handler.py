"""
webcam_handler.py
-----------------
Handles every possible video / image source for the Interview Coach.

Supported modes
---------------
  1. LIVE WEBCAM  – auto-detects the first working camera.
                    Each index is probed in a background thread with a
                    hard timeout so the app never hangs.
  2. VIDEO FILE   – plays back a pre-recorded .mp4 / .avi / .mov / etc.
  3. IMAGE FILE   – analyses a single .jpg / .png / etc. as a still frame.
  4. DEMO MODE    – generates a synthetic animated frame when no real
                    source is available (no camera required at all).

Public surface
--------------
  detect_source(source, timeout_s, demo_fallback)
      -> SourceInfo (named tuple)

  open_source(source_info)
      -> iterator that yields frames one by one

  SourceInfo
      .kind       : "webcam" | "video" | "image" | "demo"
      .path       : original path/index string (or None for demo)
      .cap        : cv2.VideoCapture or None
      .is_live    : True for webcam and demo (no discrete end)
      .description: human-readable label shown in the window title
"""

from __future__ import annotations

import os
import queue
import threading
import time
from collections import namedtuple
from typing import Iterator, Optional

import cv2
import numpy as np


# ── Constants ─────────────────────────────────────────────────────────────────
CAMERA_INDICES   = [0, 1, 2]        # Indices tried in order for webcam
PROBE_TIMEOUT_S  = 4.0              # Seconds before giving up on one camera index
DEMO_WIDTH       = 640
DEMO_HEIGHT      = 480
DEMO_FPS_DELAY   = 0.033            # ~30 fps for demo loop

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".m4v"}

# ── Named tuple returned by detect_source ────────────────────────────────────
SourceInfo = namedtuple(
    "SourceInfo",
    ["kind", "path", "cap", "is_live", "description"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Internal: threaded webcam probe
# ─────────────────────────────────────────────────────────────────────────────

def _probe_camera_index(index: int, result_q: "queue.Queue[cv2.VideoCapture | None]") -> None:
    """
    Worker run in a daemon thread.

    Opens the camera with DirectShow and puts the VideoCapture into
    *result_q* if successful, or None on failure.
    """
    try:
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            result_q.put(None)
            return
        ret, _ = cap.read()
        if not ret:
            cap.release()
            result_q.put(None)
            return
        result_q.put(cap)
    except Exception:
        result_q.put(None)


def _try_webcam_with_timeout(timeout_s: float) -> Optional[cv2.VideoCapture]:
    """
    Probe each camera index in a daemon thread; give up after *timeout_s*
    per index. Returns the first working VideoCapture or None.
    """
    for index in CAMERA_INDICES:
        print(f"[Camera] Probing index {index} (timeout {timeout_s:.1f}s)...")
        result_q: queue.Queue = queue.Queue(maxsize=1)

        t = threading.Thread(
            target=_probe_camera_index,
            args=(index, result_q),
            daemon=True,          # Dies automatically when the main thread exits
            name=f"cam-probe-{index}",
        )
        t.start()

        try:
            cap = result_q.get(timeout=timeout_s)
        except queue.Empty:
            # Thread is still blocking inside cv2.VideoCapture — abandon it.
            # The daemon flag ensures it doesn't keep the process alive.
            print(f"[Camera] Index {index} timed out after {timeout_s:.1f}s — skipping.")
            continue

        if cap is not None:
            print(f"[Camera] Index {index} is working.")
            return cap

        print(f"[Camera] Index {index} failed — trying next.")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Internal: demo frame generator
# ─────────────────────────────────────────────────────────────────────────────

def _make_demo_frame(tick: int) -> np.ndarray:
    """
    Generate a synthetic BGR frame for demo / offline mode.

    The frame has a dark gradient background, a pulsing circle that
    simulates a "face", and an overlay message so the user knows they
    are in demo mode.
    """
    frame = np.zeros((DEMO_HEIGHT, DEMO_WIDTH, 3), dtype=np.uint8)

    # Animated background gradient (hue rotates over time)
    hue = int(tick * 0.8) % 180
    bg_color = tuple(int(c) for c in cv2.cvtColor(
        np.array([[[hue, 60, 40]]], dtype=np.uint8), cv2.COLOR_HSV2BGR
    )[0][0])
    frame[:] = bg_color

    # Pulsing "face" circle
    cx, cy = DEMO_WIDTH // 2, DEMO_HEIGHT // 2
    radius = int(80 + 12 * abs(((tick % 60) / 30.0) - 1.0))   # 80–92 px
    face_hue = (hue + 90) % 180
    face_color = tuple(int(c) for c in cv2.cvtColor(
        np.array([[[face_hue, 180, 220]]], dtype=np.uint8), cv2.COLOR_HSV2BGR
    )[0][0])
    cv2.circle(frame, (cx, cy), radius, face_color, -1)
    cv2.circle(frame, (cx, cy), radius, (255, 255, 255), 2)

    # Eyes
    for ex in [cx - 25, cx + 25]:
        cv2.circle(frame, (ex, cy - 20), 8, (20, 20, 20), -1)

    # Mouth arc (simple)
    axes = (30, 15)
    cv2.ellipse(frame, (cx, cy + 20), axes, 0, 0, 180, (20, 20, 20), 3)

    # Overlay text
    _put_center_text(frame, "-- DEMO MODE --", DEMO_HEIGHT // 2 - 120,
                     scale=0.75, color=(255, 255, 255), thickness=2)
    _put_center_text(frame, "No camera detected", DEMO_HEIGHT // 2 - 95,
                     scale=0.48, color=(200, 200, 200))
    _put_center_text(frame, "Emotion analysis runs on this synthetic face",
                     DEMO_HEIGHT - 30, scale=0.42, color=(180, 180, 180))

    return frame


def _put_center_text(frame, text: str, y: int,
                     scale: float = 0.5, color=(255, 255, 255), thickness: int = 1) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, _), _ = cv2.getTextSize(text, font, scale, thickness)
    x = (frame.shape[1] - tw) // 2
    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


# ─────────────────────────────────────────────────────────────────────────────
# Public: detect_source
# ─────────────────────────────────────────────────────────────────────────────

def detect_source(
    source: Optional[str] = None,
    timeout_s: float = PROBE_TIMEOUT_S,
    demo_fallback: bool = True,
) -> SourceInfo:
    """
    Determine the best available video/image source.

    Priority order
    --------------
    1. If *source* is given, use it directly (file path or numeric index).
    2. Otherwise try live webcam with a timeout.
    3. If webcam fails and *demo_fallback* is True, enter demo mode.
    4. If *demo_fallback* is False, return a SourceInfo with kind='none'.

    Args:
        source:        Path to an image/video file, or a numeric camera
                       index as a string (e.g. "0"), or None to auto-detect.
        timeout_s:     Per-index timeout for webcam probing (seconds).
        demo_fallback: Automatically enter demo mode if no camera is found.

    Returns:
        SourceInfo named tuple.
    """
    # ── Explicit source provided ──────────────────────────────────────────────
    if source is not None:
        return _open_explicit_source(source)

    # ── Auto-detect webcam ────────────────────────────────────────────────────
    print("[Camera] Auto-detecting webcam...")
    cap = _try_webcam_with_timeout(timeout_s)
    if cap is not None:
        return SourceInfo(
            kind="webcam",
            path=None,
            cap=cap,
            is_live=True,
            description="Live Webcam",
        )

    # ── All cameras failed ────────────────────────────────────────────────────
    print("[Camera] No working webcam found.")
    if demo_fallback:
        print("[Camera] Falling back to DEMO MODE (synthetic animated face).")
        return SourceInfo(
            kind="demo",
            path=None,
            cap=None,
            is_live=True,
            description="Demo Mode (no camera)",
        )

    return SourceInfo(kind="none", path=None, cap=None, is_live=False,
                      description="No source")


def _open_explicit_source(source: str) -> SourceInfo:
    """Parse and open an explicitly provided source string."""
    # Numeric index? (e.g. "0", "1")
    if source.isdigit():
        idx = int(source)
        print(f"[Camera] Opening explicit camera index {idx}...")
        result_q: queue.Queue = queue.Queue(maxsize=1)
        t = threading.Thread(
            target=_probe_camera_index, args=(idx, result_q), daemon=True
        )
        t.start()
        try:
            cap = result_q.get(timeout=PROBE_TIMEOUT_S)
        except queue.Empty:
            cap = None

        if cap:
            return SourceInfo(kind="webcam", path=source, cap=cap,
                              is_live=True, description=f"Camera {idx}")
        print(f"[Camera] Camera index {idx} failed.")
        return SourceInfo(kind="none", path=source, cap=None,
                          is_live=False, description="No source")

    # File path
    path = os.path.abspath(source)
    if not os.path.isfile(path):
        print(f"[ERROR] File not found: {path}")
        return SourceInfo(kind="none", path=path, cap=None,
                          is_live=False, description="File not found")

    ext = os.path.splitext(path)[1].lower()

    if ext in IMAGE_EXTENSIONS:
        img = cv2.imread(path)
        if img is None:
            print(f"[ERROR] Could not read image: {path}")
            return SourceInfo(kind="none", path=path, cap=None,
                              is_live=False, description="Image unreadable")
        print(f"[Source] Image file: {os.path.basename(path)}")
        # Store the image on the SourceInfo; open_source will yield it
        info = SourceInfo(kind="image", path=path, cap=img,
                          is_live=False, description=f"Image: {os.path.basename(path)}")
        return info

    if ext in VIDEO_EXTENSIONS:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print(f"[ERROR] Could not open video: {path}")
            return SourceInfo(kind="none", path=path, cap=None,
                              is_live=False, description="Video unreadable")
        print(f"[Source] Video file: {os.path.basename(path)}")
        return SourceInfo(kind="video", path=path, cap=cap,
                          is_live=False, description=f"Video: {os.path.basename(path)}")

    print(f"[ERROR] Unsupported file type '{ext}'. "
          f"Images: {IMAGE_EXTENSIONS}  Videos: {VIDEO_EXTENSIONS}")
    return SourceInfo(kind="none", path=path, cap=None,
                      is_live=False, description="Unsupported file type")


# ─────────────────────────────────────────────────────────────────────────────
# Public: open_source  — unified frame iterator
# ─────────────────────────────────────────────────────────────────────────────

def open_source(info: SourceInfo) -> Iterator[np.ndarray]:
    """
    Yield frames from *info* one by one.

    Webcam / Video  → yields frames from cv2.VideoCapture
    Image           → yields the same still frame indefinitely
                      (caller breaks on 'Q')
    Demo            → generates synthetic frames at ~30 fps

    Raises:
        ValueError: if info.kind is 'none'.
    """
    if info.kind == "none":
        raise ValueError("Cannot open a source of kind 'none'.")

    if info.kind in ("webcam", "video"):
        cap: cv2.VideoCapture = info.cap
        while True:
            ret, frame = cap.read()
            if not ret:
                if info.kind == "video":
                    print("[Source] Video finished.")
                else:
                    print("[ERROR] Webcam read failed (disconnected?).")
                break
            yield frame
        cap.release()

    elif info.kind == "image":
        # The stored frame (numpy array) is in info.cap for images
        still: np.ndarray = info.cap
        while True:
            # Yield a copy so downstream drawing doesn't corrupt the original
            yield still.copy()

    elif info.kind == "demo":
        tick = 0
        while True:
            frame = _make_demo_frame(tick)
            tick += 1
            time.sleep(DEMO_FPS_DELAY)
            yield frame
