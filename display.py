"""
display.py
----------
All OpenCV drawing/overlay helpers for the Interview Coach.

Layout (top → bottom)
----------------------
  [TIMELINE BAR ]  40px  — compact dot-per-reading emotion history
  [  WEBCAM FEED ]        — full camera image (primary content)
  [  HUD SIDEBAR ]  right 220px — live analytics panel drawn ON the feed
  [ QUESTION BAR ]  36px  — current interview question
  [   TIP BANNER ]  70px  — coaching tip + emotion label + confidence

Design tokens
-------------
  All colours, sizes, and alpha values are defined in constants at the top
  so they are easy to tune in one place.
"""

from __future__ import annotations

import time

import cv2
import numpy as np


# ═══════════════════════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════════════════════

FONT       = cv2.FONT_HERSHEY_SIMPLEX
FONT_BOLD  = cv2.FONT_HERSHEY_DUPLEX   # Slightly heavier for headings

# Layout heights (px)
TIMELINE_H  = 40    # Top emotion-timeline bar
TIP_H       = 70    # Bottom coaching-tip banner
QUESTION_H  = 34    # Question strip just above the tip
SIDEBAR_W   = 220   # Width of the right-side live-analytics panel

# Colours (BGR)
C_BG_DARK   = (18,  18,  24)   # Near-black panel background
C_BG_MED    = (30,  32,  42)   # Slightly lighter panel fill
C_ACCENT    = (0,   200, 160)  # Teal accent — used for headings and highlights
C_TEXT_PRI  = (230, 230, 230)  # Primary text
C_TEXT_SEC  = (150, 155, 165)  # Secondary / muted text
C_DIVIDER   = (50,  52,  65)   # Hairline rule colour

# Per-emotion colour palette (BGR) — single source of truth
EMOTION_COLORS: dict[str, tuple] = {
    "happy":    (0,   200, 80),
    "neutral":  (180, 180, 0),
    "sad":      (0,   110, 200),
    "angry":    (0,   40,  210),
    "fear":     (170, 0,   170),
    "surprise": (0,   160, 220),
    "disgust":  (0,   150, 120),
    "unknown":  (120, 120, 120),
}


def emotion_color(emotion: str) -> tuple:
    """Return the BGR colour for *emotion*, falling back to grey."""
    return EMOTION_COLORS.get(emotion.lower(), EMOTION_COLORS["unknown"])


# ═══════════════════════════════════════════════════════════════════════════════
#  1.  TIMELINE BAR  (top strip)
# ═══════════════════════════════════════════════════════════════════════════════

def draw_timeline_bar(frame: np.ndarray, history: list[dict]) -> None:
    """
    Draw a compact dot-based emotion timeline across the top of the frame.

    Each dot represents one DeepFace reading; colour = emotion; size scales
    with confidence.  The most recent readings fill right-to-left so the
    newest sample is always at the right edge.

    Args:
        frame:   Current BGR frame (drawn on in-place).
        history: Full session history from session_logger.get_history().
    """
    h_f, w_f = frame.shape[:2]

    # ── Dark strip background ──────────────────────────────────────────────────
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w_f, TIMELINE_H), C_BG_DARK, -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    # Thin accent line at the bottom of the strip
    cv2.line(frame, (0, TIMELINE_H - 1), (w_f, TIMELINE_H - 1), C_DIVIDER, 1)

    if not history:
        _put_text(frame, "Waiting for face detection...",
                  (12, TIMELINE_H // 2 + 5), scale=0.38, color=C_TEXT_SEC)
        return

    # ── Label on the left ─────────────────────────────────────────────────────
    label = "HISTORY"
    _put_text(frame, label, (10, TIMELINE_H // 2 + 5),
              scale=0.35, color=C_ACCENT, thickness=1)
    lw, _ = cv2.getTextSize(label, FONT, 0.35, 1)[0]
    left_margin = lw + 20

    # ── Dots ──────────────────────────────────────────────────────────────────
    # How many dots fit in the available width?
    dot_r    = 7    # dot radius (px)
    spacing  = dot_r * 2 + 6
    usable_w = w_f - left_margin - 10
    max_dots = usable_w // spacing

    recent = history[-max_dots:]   # keep only what fits
    cy     = TIMELINE_H // 2

    for i, rec in enumerate(recent):
        cx    = left_margin + i * spacing + dot_r
        color = emotion_color(rec["emotion"])
        conf  = rec["confidence"]          # 0–100
        r     = max(4, min(dot_r, int(dot_r * conf / 80)))   # size by confidence

        cv2.circle(frame, (cx, cy), r + 1, C_BG_DARK, -1)   # dark outline
        cv2.circle(frame, (cx, cy), r,     color,     -1)

    # Label the rightmost dot's emotion
    if recent:
        last_rec   = recent[-1]
        last_cx    = left_margin + (len(recent) - 1) * spacing + dot_r
        last_color = emotion_color(last_rec["emotion"])
        tag        = last_rec["emotion"].upper()[:4]          # e.g. "HAPP"
        _put_text(frame, tag, (last_cx - 12, cy - dot_r - 4),
                  scale=0.30, color=last_color, thickness=1)


# ═══════════════════════════════════════════════════════════════════════════════
#  2.  FACE BOX + EMOTION LABEL  (overlaid on video feed)
# ═══════════════════════════════════════════════════════════════════════════════

def draw_face_box(frame: np.ndarray, region: dict, color: tuple) -> None:
    """Draw a 2-px coloured rectangle around the detected face."""
    x, y = region.get("x", 0), region.get("y", 0)
    w, h = region.get("w", 0), region.get("h", 0)
    if w > 0 and h > 0:
        # Slightly rounded feel via corner ticks
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        # Corner accents (3-px squares at each corner for a modern look)
        tk = 6
        for cx, cy in [(x, y), (x+w, y), (x, y+h), (x+w, y+h)]:
            cv2.rectangle(frame, (cx - 1, cy - 1), (cx + 1, cy + 1), (255, 255, 255), -1)


def draw_emotion_label(frame: np.ndarray, label: str, region: dict, color: tuple) -> None:
    """Draw the emotion label tag above the face bounding box."""
    x = region.get("x", 0)
    y = region.get("y", 0)
    text_y = max(y - 10, TIMELINE_H + 18)

    # Pill-shaped background
    (tw, th), _ = cv2.getTextSize(label, FONT, 0.60, 2)
    pad = 4
    cv2.rectangle(
        frame,
        (x - pad, text_y - th - pad),
        (x + tw + pad, text_y + pad),
        (*color[:3],),    # same colour, filled
        -1,
    )
    # White text on coloured pill
    cv2.putText(frame, label, (x, text_y), FONT, 0.60, (255, 255, 255), 2, cv2.LINE_AA)


# ═══════════════════════════════════════════════════════════════════════════════
#  3.  LIVE ANALYTICS SIDEBAR  (right panel, drawn on the feed)
# ═══════════════════════════════════════════════════════════════════════════════

def draw_analytics_sidebar(
    frame: np.ndarray,
    emotion: str,
    confidence: float,
    history: list[dict],
    session_seconds: float,
) -> None:
    """
    Draw a semi-transparent analytics panel on the right side of the frame.

    Displays:
      • Current emotion + confidence bar
      • Session duration
      • Dominant emotion (session-wide)
      • Average confidence (session-wide)
      • Per-emotion frequency counts (top 4)

    Args:
        frame:           Current BGR frame.
        emotion:         Current dominant emotion string.
        confidence:      Current emotion confidence (0–100).
        history:         Full session history list.
        session_seconds: Elapsed session time in seconds.
    """
    h_f, w_f = frame.shape[:2]

    # Sidebar bounds
    sx = w_f - SIDEBAR_W
    sy = TIMELINE_H + 4
    ey = h_f - TIP_H - QUESTION_H - 4

    if ey <= sy + 20:
        return   # Frame too small — skip sidebar

    # ── Semi-transparent background ────────────────────────────────────────────
    overlay = frame.copy()
    cv2.rectangle(overlay, (sx, sy), (w_f, ey), C_BG_DARK, -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

    # Left edge accent line
    cv2.line(frame, (sx, sy), (sx, ey), C_ACCENT, 2)

    # ── Helper: y cursor ──────────────────────────────────────────────────────
    x0  = sx + 10
    row = [sy + 18]   # mutable cursor via list so nested fn can update it

    def nl(extra: int = 0) -> int:
        """Advance the y cursor and return the new y position."""
        row[0] += 18 + extra
        return row[0]

    def divider():
        cv2.line(frame, (sx + 4, row[0] + 6), (w_f - 4, row[0] + 6), C_DIVIDER, 1)
        row[0] += 14

    # ── Section: Current ──────────────────────────────────────────────────────
    _put_text(frame, "LIVE", (x0, row[0]), scale=0.38, color=C_ACCENT, thickness=1)

    # Emotion tag
    color = emotion_color(emotion)
    _put_text(frame, emotion.upper(), (x0, nl(2)),
              scale=0.62, color=color, thickness=2)

    # Confidence label
    _put_text(frame, f"Confidence: {confidence:.1f}%", (x0, nl(2)),
              scale=0.38, color=C_TEXT_SEC)

    # Confidence bar
    bar_y  = nl(4)
    bar_w  = SIDEBAR_W - 24
    bar_h  = 8
    fill_w = int(bar_w * min(confidence, 100) / 100)
    cv2.rectangle(frame, (x0, bar_y), (x0 + bar_w, bar_y + bar_h), C_BG_MED, -1)
    if fill_w > 0:
        cv2.rectangle(frame, (x0, bar_y), (x0 + fill_w, bar_y + bar_h), color, -1)
    row[0] += bar_h

    divider()

    # ── Section: Session ──────────────────────────────────────────────────────
    _put_text(frame, "SESSION", (x0, row[0]), scale=0.38, color=C_ACCENT, thickness=1)

    mins, secs = divmod(int(session_seconds), 60)
    _put_text(frame, f"Duration : {mins:02d}m {secs:02d}s", (x0, nl(2)),
              scale=0.38, color=C_TEXT_PRI)

    total = len(history)
    _put_text(frame, f"Readings : {total}", (x0, nl()),
              scale=0.38, color=C_TEXT_PRI)

    # Dominant emotion (session-wide)
    if history:
        counts: dict[str, int] = {}
        for r in history:
            counts[r["emotion"]] = counts.get(r["emotion"], 0) + 1
        dominant = max(counts, key=counts.get)
        dom_conf_vals = [r["confidence"] for r in history if r["emotion"] == dominant]
        dom_conf = sum(dom_conf_vals) / len(dom_conf_vals) if dom_conf_vals else 0.0

        dom_color = emotion_color(dominant)
        _put_text(frame, f"Dominant :", (x0, nl()),
                  scale=0.38, color=C_TEXT_SEC)
        _put_text(frame, dominant.upper(), (x0 + 76, row[0]),
                  scale=0.38, color=dom_color, thickness=1)

        all_confs = [r["confidence"] for r in history]
        avg_conf  = sum(all_confs) / len(all_confs) if all_confs else 0.0
        _put_text(frame, f"Avg conf : {avg_conf:.1f}%", (x0, nl()),
                  scale=0.38, color=C_TEXT_PRI)

        divider()

        # ── Section: Emotion breakdown (top 4) ────────────────────────────────
        if row[0] < ey - 60:
            _put_text(frame, "BREAKDOWN", (x0, row[0]),
                      scale=0.38, color=C_ACCENT, thickness=1)

            top4 = sorted(counts.items(), key=lambda kv: -kv[1])[:4]
            bar_max_w = SIDEBAR_W - 28

            for emo, cnt in top4:
                if row[0] + 26 > ey - 8:
                    break
                pct      = cnt / total * 100
                e_color  = emotion_color(emo)

                nl(4)
                _put_text(frame, f"{emo:<8} {pct:4.0f}%", (x0, row[0]),
                          scale=0.35, color=C_TEXT_PRI)

                # Mini bar
                bw = int(bar_max_w * pct / 100)
                bh = 5
                by = row[0] + 3
                cv2.rectangle(frame, (x0, by), (x0 + bar_max_w, by + bh), C_BG_MED, -1)
                if bw > 0:
                    cv2.rectangle(frame, (x0, by), (x0 + bw, by + bh), e_color, -1)
                row[0] += bh


# ═══════════════════════════════════════════════════════════════════════════════
#  4.  QUESTION BANNER  (above tip)
# ═══════════════════════════════════════════════════════════════════════════════

def draw_question_banner(frame: np.ndarray, category: str, question: str) -> None:
    """
    Render the current interview question in a slim strip just above the
    coaching tip banner.

    Args:
        category: Question category (e.g. 'Behavioural').
        question: Full question text (truncated to fit).
    """
    h_f, w_f = frame.shape[:2]
    by = h_f - TIP_H - QUESTION_H

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, by), (w_f, by + QUESTION_H), (10, 45, 55), -1)
    cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

    # Accent left-edge bar
    cv2.rectangle(frame, (0, by), (3, by + QUESTION_H), C_ACCENT, -1)

    # Category tag
    tag = f"[{category.upper()}]"
    _put_text(frame, tag, (10, by + 14), scale=0.38, color=C_ACCENT, thickness=1)
    tw, _ = cv2.getTextSize(tag, FONT, 0.38, 1)[0]

    # Question text — truncated to available width
    avail_w = w_f - tw - SIDEBAR_W - 24
    max_chars = max(10, avail_w // 8)
    short_q = question if len(question) <= max_chars else question[:max_chars - 3] + "..."
    _put_text(frame, short_q, (tw + 18, by + 25), scale=0.42, color=C_TEXT_PRI)


# ═══════════════════════════════════════════════════════════════════════════════
#  5.  COACHING TIP BANNER  (bottom)
# ═══════════════════════════════════════════════════════════════════════════════

def draw_tip_banner(frame: np.ndarray, tip: str, color: tuple) -> None:
    """
    Draw a slim coaching tip banner at the very bottom of the frame.

    The banner is taller than before so two tip lines fit comfortably.
    """
    h_f, w_f = frame.shape[:2]
    by = h_f - TIP_H

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, by), (w_f, h_f), C_BG_DARK, -1)
    cv2.addWeighted(overlay, 0.88, frame, 0.12, 0, frame)

    # Coloured top border
    cv2.line(frame, (0, by), (w_f, by), color, 2)

    # "Coach:" label
    _put_text(frame, "Coach:", (10, by + 18), scale=0.42, color=color, thickness=1)

    # Tip text — up to 2 wrapped lines
    usable_w = w_f - SIDEBAR_W - 20
    max_chars = max(10, usable_w // 9)
    lines = _wrap_text(tip, max_chars)
    for i, line in enumerate(lines[:2]):
        _put_text(frame, line, (10, by + 36 + i * 22),
                  scale=0.44, color=C_TEXT_PRI)


# ═══════════════════════════════════════════════════════════════════════════════
#  6.  HUD CHROME  (quit hint, source tag, status)
# ═══════════════════════════════════════════════════════════════════════════════

def draw_quit_hint(frame: np.ndarray) -> None:
    """Small 'Q: quit' hint in the top-right corner of the timeline bar."""
    h_f, w_f = frame.shape[:2]
    text = "Q: quit"
    tw, _ = cv2.getTextSize(text, FONT, 0.38, 1)[0]
    _put_text(frame, text, (w_f - SIDEBAR_W - tw - 14, TIMELINE_H - 10),
              scale=0.38, color=C_TEXT_SEC)


def draw_source_tag(frame: np.ndarray, description: str) -> None:
    """Tiny source-type label at the bottom-right inside the sidebar area."""
    h_f, w_f = frame.shape[:2]
    _put_text(frame, description, (w_f - SIDEBAR_W + 4, h_f - 6),
              scale=0.30, color=C_TEXT_SEC)


def draw_status(frame: np.ndarray, message: str) -> None:
    """Centred status message shown while DeepFace is warming up."""
    h_f, w_f = frame.shape[:2]
    (tw, th), _ = cv2.getTextSize(message, FONT, 0.65, 2)
    x = (w_f - tw) // 2
    y = (h_f + th) // 2
    # Drop-shadow for readability
    cv2.putText(frame, message, (x + 2, y + 2), FONT, 0.65, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(frame, message, (x, y), FONT, 0.65, C_ACCENT, 2, cv2.LINE_AA)


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _put_text(
    frame: np.ndarray,
    text: str,
    pos: tuple,
    scale: float = 0.45,
    color: tuple = C_TEXT_PRI,
    thickness: int = 1,
    font=None,
) -> None:
    """Convenience wrapper around cv2.putText with sane defaults."""
    cv2.putText(frame, text, pos, font or FONT, scale, color, thickness, cv2.LINE_AA)


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """Word-wrap *text* into lines of at most *max_chars* characters."""
    words   = text.split()
    lines   = []
    current = ""
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
