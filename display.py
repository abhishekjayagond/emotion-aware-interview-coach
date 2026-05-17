"""
display.py
----------
Modern Immersive AI Interview Assistant.
Features comprehensive coaching analytics, cinematic framing, and session summaries.
"""

from __future__ import annotations

import time
import math
import random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# ═══════════════════════════════════════════════════════════════════════════════
#  DESIGN TOKENS & STATE
# ═══════════════════════════════════════════════════════════════════════════════

C_BG_DARK   = (6,   10,  14)
C_ACCENT    = (230, 150, 70)
C_TEXT_PRI  = (255, 255, 255)
C_TEXT_SEC  = (170, 185, 200)
C_SUCCESS   = (140, 220, 140)
C_WARNING   = (60,  160, 240)
C_DANGER    = (80,  80,  255)

EMOTION_COLORS: dict[str, tuple] = {
    "happy":    (140, 220, 140),
    "neutral":  (230, 230, 230),
    "sad":      (240, 180, 120),
    "angry":    (100, 100, 240),
    "fear":     (200, 120, 200),
    "surprise": (120, 220, 240),
    "disgust":  (120, 190, 140),
    "unknown":  (160, 160, 160),
}

_state = {
    "fps_start": time.time(),
    "frames": 0,
    "fps": 0.0,
    "smooth_conf": 0.0,
    "last_face_time": 0.0,
    "eye_contact_ratio": 1.0,
    "composure_score": 100.0,
    "history_composure": [],
    "waveform_phase": 0.0,
    "vignette_mask": None
}


# ═══════════════════════════════════════════════════════════════════════════════
#  TYPOGRAPHY (PIL)
# ═══════════════════════════════════════════════════════════════════════════════

_FONTS = {}
try:
    _FONTS["tiny"]    = ImageFont.truetype("segoeui.ttf", 11)
    _FONTS["small"]   = ImageFont.truetype("segoeui.ttf", 14)
    _FONTS["main"]    = ImageFont.truetype("segoeui.ttf", 16)
    _FONTS["large"]   = ImageFont.truetype("segoeui.ttf", 22)
    _FONTS["bold"]    = ImageFont.truetype("segoeuib.ttf", 14)
    _FONTS["xlarge"]  = ImageFont.truetype("segoeuib.ttf", 30)
    _FONTS["title"]   = ImageFont.truetype("segoeuib.ttf", 40)
except IOError:
    df = ImageFont.load_default()
    _FONTS = {k: df for k in ["tiny", "small", "main", "large", "bold", "xlarge", "title"]}

def emotion_color(emotion: str) -> tuple:
    return EMOTION_COLORS.get(emotion.lower(), EMOTION_COLORS["unknown"])

def _put_text(frame, text, pos, color=C_TEXT_PRI, font_type="main"):
    img_pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(img_pil)
    draw.text(pos, text, font=_FONTS.get(font_type, _FONTS["main"]), fill=color)
    frame[:] = np.array(img_pil)

def _get_text_size(text, font_type="main"):
    font = _FONTS.get(font_type, _FONTS["main"])
    if hasattr(font, "getbbox"):
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    return 0, 0


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def apply_cinematic_vignette(frame: np.ndarray, intensity: float = 0.4) -> None:
    """Applies a soft darkened edge vignette for premium Zoom/Meet feel."""
    h, w = frame.shape[:2]
    if _state["vignette_mask"] is None or _state["vignette_mask"].shape[:2] != (h, w):
        X_kernel = cv2.getGaussianKernel(w, w/1.5)
        Y_kernel = cv2.getGaussianKernel(h, h/1.5)
        kernel = Y_kernel * X_kernel.T
        mask = kernel / kernel.max()
        mask = (1.0 - intensity) + mask * intensity
        _state["vignette_mask"] = np.dstack([mask, mask, mask]).astype(np.float32)
        
    frame[:] = np.clip(frame * _state["vignette_mask"], 0, 255).astype(np.uint8)


def _glass_panel(frame, x, y, w, h, radius=16, alpha=0.88, blur=45):
    h_f, w_f = frame.shape[:2]
    x1, y1 = max(0, int(x)), max(0, int(y))
    x2, y2 = min(w_f, int(x + w)), min(h_f, int(y + h))
    if x2 <= x1 or y2 <= y1: return

    roi = frame[y1:y2, x1:x2].copy()
    ksize = blur if blur % 2 == 1 else blur + 1
    blurred = cv2.GaussianBlur(roi, (ksize, ksize), 0) if blur > 0 else roi
    
    dark = np.full(blurred.shape, C_BG_DARK, dtype=np.uint8)
    glass = cv2.addWeighted(blurred, 0.45, dark, 0.55, 0)
    
    mask = Image.new("L", (x2 - x1, y2 - y1), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, x2 - x1 - 1, y2 - y1 - 1), radius, fill=int(255 * alpha))
    mask_np = np.array(mask, dtype=np.float32) / 255.0
    
    for c in range(3):
        frame[y1:y2, x1:x2, c] = (glass[:, :, c] * mask_np + roi[:, :, c] * (1.0 - mask_np)).astype(np.uint8)


# ═══════════════════════════════════════════════════════════════════════════════
#  UI COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════

def draw_top_hud(frame: np.ndarray, session_info: dict) -> None:
    h_f, w_f = frame.shape[:2]
    hud_w = max(500, int(w_f * 0.45))
    hud_h = 44
    x = (w_f - hud_w) // 2
    y = 20
    
    _glass_panel(frame, x, y, hud_w, hud_h, radius=22, alpha=0.9, blur=35)
    
    stage_text = f"Stage {session_info['stage_idx']}/{session_info['total_stages']}: {session_info['stage_name']}"
    _put_text(frame, stage_text, (x + 25, y + 12), color=C_TEXT_PRI, font_type="small")
    
    q_text = f"Q{session_info['q_count']}"
    _put_text(frame, q_text, (x + 30 + _get_text_size(stage_text, "small")[0] + 15, y + 12), color=C_ACCENT, font_type="bold")

    diff_text = f"Difficulty: {session_info['difficulty']}"
    _put_text(frame, diff_text, (x + 30 + _get_text_size(stage_text, "small")[0] + 60, y + 12), color=C_TEXT_SEC, font_type="tiny")

    mins, secs = divmod(int(session_info["elapsed"]), 60)
    timer_text = f"{mins:02d}:{secs:02d}"
    tw, _ = _get_text_size(timer_text, "small")
    
    _put_text(frame, timer_text, (x + hud_w - tw - 25, y + 12), color=C_TEXT_PRI, font_type="small")
    
    pulse = (math.sin(time.time() * 4) + 1) / 2
    dot_color = (int(C_DANGER[0] * pulse), int(C_DANGER[1] * pulse), int(C_DANGER[2] * pulse))
    cv2.circle(frame, (x + hud_w - tw - 40, y + hud_h // 2), 5, dot_color, -1)


def draw_face_box(frame: np.ndarray, region: dict, color: tuple) -> None:
    x, y = region.get("x", 0), region.get("y", 0)
    w, h = region.get("w", 0), region.get("h", 0)
    if w <= 0 or h <= 0: return

    _state["last_face_time"] = time.time()
    l, t = int(min(w, h) * 0.10), 2 
    
    pts = [
        ((x, y), (x+l, y), (x, y+l)), ((x+w, y), (x+w-l, y), (x+w, y+l)),
        ((x, y+h), (x+l, y+h), (x, y+h-l)), ((x+w, y+h), (x+w-l, y+h), (x+w, y+h-l))
    ]
    overlay = frame.copy()
    for (p1, p2, p3) in pts:
        cv2.line(overlay, p1, p2, color, t)
        cv2.line(overlay, p1, p3, color, t)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)


def draw_analytics_sidebar(frame: np.ndarray, emotion: str, confidence: float, history: list[dict], session_info: dict) -> None:
    h_f, w_f = frame.shape[:2]
    hud_w, hud_h = 260, 420
    x, y = w_f - hud_w - 20, 80
    
    if x < 100 or h_f < 500: return

    _glass_panel(frame, x, y, hud_w, hud_h, radius=20, alpha=0.9, blur=50)
    
    x0, y_cursor = x + 25, y + 25
    def nl(dy=24): nonlocal y_cursor; y_cursor += dy
    def div(): nonlocal y_cursor; cv2.line(frame, (x0, y_cursor), (x+hud_w-25, y_cursor), (60, 60, 60), 1); nl(15)
    
    _put_text(frame, "Behavioral State", (x0, y_cursor), color=C_TEXT_SEC, font_type="small")
    nl(25)

    e_color = emotion_color(emotion)
    _put_text(frame, emotion.capitalize(), (x0, y_cursor), color=e_color, font_type="xlarge")
    nl(45)

    _state["smooth_conf"] += (confidence - _state["smooth_conf"]) * 0.15
    conf_val = _state["smooth_conf"]
    _put_text(frame, f"Confidence: {conf_val:.1f}%", (x0, y_cursor), color=C_TEXT_PRI, font_type="small")
    nl(18)
    
    bar_w = hud_w - 50
    cv2.rectangle(frame, (x0, y_cursor), (x0 + bar_w, y_cursor + 3), (50, 50, 50), -1)
    if conf_val > 0:
        cv2.rectangle(frame, (x0, y_cursor), (x0 + int((conf_val/100)*bar_w), y_cursor + 3), e_color, -1)
    nl(25)
    div()

    _put_text(frame, "Composure Scorecard", (x0, y_cursor), color=C_TEXT_SEC, font_type="small")
    nl(25)

    target_composure = 100.0
    if history:
        recent = history[-15:]
        nervous = [r["scores"].get("fear", 0) + r["scores"].get("sad", 0) for r in recent]
        target_composure = max(0.0, 100.0 - sum(nervous)/len(nervous))
    _state["composure_score"] = _state["composure_score"] * 0.9 + target_composure * 0.1
    comp_pct = _state["composure_score"]

    _put_text(frame, "Stability:", (x0, y_cursor), color=C_TEXT_PRI, font_type="small")
    _put_text(frame, f"{comp_pct:.0f}/100", (x0 + 140, y_cursor), color=C_SUCCESS if comp_pct > 60 else C_WARNING, font_type="bold")
    nl(25)
    div()

    _put_text(frame, "Stability Trend", (x0, y_cursor), color=C_TEXT_SEC, font_type="small")
    nl(20)
    
    _state["history_composure"].append(comp_pct)
    if len(_state["history_composure"]) > 50: _state["history_composure"].pop(0)

    chart_h, chart_w = 40, hud_w - 50
    pts = []
    for i, val in enumerate(_state["history_composure"]):
        px = x0 + int((i / max(1, len(_state["history_composure"]) - 1)) * chart_w)
        py = y_cursor + chart_h - int((val / 100.0) * chart_h)
        pts.append((px, py))
    
    if len(pts) > 1:
        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], False, C_ACCENT, 2, cv2.LINE_AA)
    nl(chart_h + 20)
    div()

    _put_text(frame, "AI Interviewer Reacts:", (x0, y_cursor), color=C_TEXT_SEC, font_type="small")
    nl(25)
    
    insight_text = "Positive impression. Keep it up." if comp_pct > 60 else "Candidate seems anxious. Easing up."
    _put_text(frame, insight_text, (x0, y_cursor), color=C_TEXT_PRI, font_type="small")


def draw_audio_hud(frame: np.ndarray, session_info: dict) -> None:
    h_f, w_f = frame.shape[:2]
    hud_w, hud_h = 260, 130
    x, y = 20, h_f - hud_h - 25
    
    if w_f < 800: return
    
    _glass_panel(frame, x, y, hud_w, hud_h, radius=20, alpha=0.9, blur=45)
    
    x0, y0 = x + 25, y + 20
    _put_text(frame, "Communication Metrics", (x0, y0), color=C_TEXT_SEC, font_type="small")
    
    _state["waveform_phase"] += 0.3
    phase = _state["waveform_phase"]
    is_listening = session_info["state"] == "LISTENING"
    
    base_y = y0 + 40
    wave_w = hud_w - 50
    
    pts = []
    for i in range(wave_w):
        amp = 15.0 if is_listening else 2.0
        noise = random.uniform(-1, 1) * amp * 0.3 if is_listening else 0
        y_wave = math.sin(i * 0.1 + phase) * amp + math.sin(i * 0.05 - phase*0.5) * (amp*0.5) + noise
        envelope = math.sin((i / wave_w) * math.pi)
        pts.append((x0 + i, int(base_y + y_wave * envelope)))
        
    if len(pts) > 1:
        wave_color = C_SUCCESS if is_listening else (100, 100, 100)
        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], False, wave_color, 2, cv2.LINE_AA)
        
    y1 = base_y + 30
    _put_text(frame, "Pace:", (x0, y1), color=C_TEXT_SEC, font_type="tiny")
    pace = session_info["speech"]["pace_wpm"]
    _put_text(frame, f"{int(pace)} WPM", (x0 + 40, y1), color=C_TEXT_PRI, font_type="tiny")
    
    _put_text(frame, "Fillers:", (x0 + 120, y1), color=C_TEXT_SEC, font_type="tiny")
    fillers = session_info["speech"]["filler_words"]
    _put_text(frame, str(fillers), (x0 + 165, y1), color=C_WARNING if fillers > 5 else C_SUCCESS, font_type="tiny")
    
    mins, secs = divmod(int(session_info["speech"]["response_time"]), 60)
    _put_text(frame, f"Resp. Time: {mins:02d}:{secs:02d}", (x0, y1 + 20), color=C_TEXT_SEC, font_type="tiny")


def draw_interview_card(frame: np.ndarray, question: str, tip: str, session_info: dict) -> None:
    h_f, w_f = frame.shape[:2]
    panel_w = int(w_f * 0.60)
    panel_w = max(450, min(panel_w, 850))
    panel_h = 130
    
    x = (w_f - panel_w) // 2 + (80 if w_f >= 800 else 0)
    y = h_f - panel_h - 25
    
    if w_f < 600: return
    _glass_panel(frame, x, y, panel_w, panel_h, radius=24, alpha=0.9, blur=45)
    
    s_state = session_info["state"]
    if s_state == "GENERATING":
        status_txt, status_col = "Generating next question...", C_WARNING
    elif s_state == "ANALYZING":
        status_txt, status_col = "Analyzing response...", C_ACCENT
    else:
        status_txt, status_col = "Listening...", C_SUCCESS

    alpha = math.sin(time.time() * 5) * 0.2 + 0.8
    s_col = (int(status_col[0]*alpha), int(status_col[1]*alpha), int(status_col[2]*alpha))
    
    _put_text(frame, status_txt, (x + 30, y + 20), color=s_col, font_type="small")

    avail_w = panel_w - 60
    max_chars = max(10, int((avail_w / 100) * 12))
    short_q = question if len(question) <= max_chars else question[:max_chars - 3] + "..."
    
    if s_state == "GENERATING":
        chars_to_show = int(session_info["state_elapsed"] * 45)
        display_q = short_q[:chars_to_show]
    else:
        display_q = short_q

    _put_text(frame, display_q, (x + 30, y + 50), color=C_TEXT_PRI, font_type="large")
    
    if s_state == "LISTENING" and session_info["state_elapsed"] > 2.0:
        short_tip = tip if len(tip) <= max_chars else tip[:max_chars - 3] + "..."
        fade = min(1.0, (session_info["state_elapsed"] - 2.0) * 1.5)
        tip_col = (int(C_TEXT_SEC[0]*fade), int(C_TEXT_SEC[1]*fade), int(C_TEXT_SEC[2]*fade))
        _put_text(frame, f"Coach: {short_tip}", (x + 30, y + 90), color=tip_col, font_type="small")


def draw_session_summary(frame: np.ndarray, session_info: dict, history: list[dict]) -> None:
    """End-of-session product summary overlay."""
    h_f, w_f = frame.shape[:2]
    
    # Blur background heavily
    ksize = 85
    blurred = cv2.GaussianBlur(frame, (ksize, ksize), 0)
    dark = np.full(blurred.shape, C_BG_DARK, dtype=np.uint8)
    frame[:] = cv2.addWeighted(blurred, 0.4, dark, 0.6, 0)
    
    panel_w = max(550, int(w_f * 0.55))
    panel_h = max(380, int(h_f * 0.6))
    x = (w_f - panel_w) // 2
    y = (h_f - panel_h) // 2
    
    _glass_panel(frame, x, y, panel_w, panel_h, radius=24, alpha=0.95, blur=0)
    
    x0, y0 = x + 40, y + 40
    
    _put_text(frame, "Interview Session Summary", (x0, y0), color=C_TEXT_PRI, font_type="title")
    
    mins, secs = divmod(int(session_info["elapsed"]), 60)
    _put_text(frame, f"Duration: {mins:02d}:{secs:02d}   •   Questions Answered: {session_info['q_count']}", (x0, y0 + 60), color=C_TEXT_SEC, font_type="main")
    
    cv2.line(frame, (x0, y0 + 100), (x + panel_w - 40, y0 + 100), (60, 60, 60), 1)
    
    # Stats
    y1 = y0 + 130
    _put_text(frame, "Overall Composure:", (x0, y1), color=C_TEXT_SEC, font_type="large")
    avg_comp = sum(_state["history_composure"])/max(1, len(_state["history_composure"])) if _state["history_composure"] else 100.0
    _put_text(frame, f"{avg_comp:.0f}/100", (x0 + 220, y1), color=C_SUCCESS if avg_comp > 60 else C_WARNING, font_type="large")
    
    y1 += 40
    _put_text(frame, "Pace Average:", (x0, y1), color=C_TEXT_SEC, font_type="large")
    _put_text(frame, f"{int(session_info['speech']['pace_wpm'])} WPM", (x0 + 220, y1), color=C_TEXT_PRI, font_type="large")

    y1 += 40
    _put_text(frame, "Filler Words:", (x0, y1), color=C_TEXT_SEC, font_type="large")
    _put_text(frame, f"{session_info['speech']['filler_words']}", (x0 + 220, y1), color=C_TEXT_PRI, font_type="large")

    cv2.line(frame, (x0, y1 + 40), (x + panel_w - 40, y1 + 40), (60, 60, 60), 1)
    
    y2 = y1 + 70
    _put_text(frame, "Key Coaching Takeaway:", (x0, y2), color=C_ACCENT, font_type="bold")
    takeaway = "Excellent stability and pace. You are highly prepared for technical rounds." if avg_comp > 75 else "Try to take deep breaths between responses to reduce filler words and anxiety."
    _put_text(frame, takeaway, (x0, y2 + 30), color=C_TEXT_PRI, font_type="main")
    
    _put_text(frame, "Press Q or Enter to exit.", (x + panel_w // 2 - 100, y + panel_h - 40), color=C_TEXT_SEC, font_type="small")


def draw_status(frame: np.ndarray, message: str) -> None:
    h_f, w_f = frame.shape[:2]
    tw, th = _get_text_size(message, "large")
    x, y = (w_f - tw) // 2, (h_f + th) // 2
    _glass_panel(frame, x - 35, y - th - 30, tw + 70, th + 60, radius=24, alpha=0.9, blur=45)
    _put_text(frame, message, (x, y - th - 5), color=C_TEXT_PRI, font_type="large")
