"""
session_summary.py
------------------
Generates the post-session analysis report:
  • Formatted text summary printed to stdout
  • Dark-themed Matplotlib PNG with three panels:
      1. Emotion timeline (coloured scatter + step line, dot size = confidence)
      2. Emotion frequency bar chart (count + %)
      3. Average confidence per emotion (horizontal bar)
"""

from __future__ import annotations

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")          # Headless — no Tk/display dependency
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

from session_logger import (
    get_history,
    get_emotion_counts,
    get_dominant_emotion,
    get_avg_confidence,
    get_session_duration,
    _session_start,               # used only for filename timestamp
)


# ── Shared colour palette (hex, matches display.py BGR palette) ───────────────
EMOTION_COLORS: dict[str, str] = {
    "happy":    "#00C850",
    "neutral":  "#B4B400",
    "sad":      "#0070C8",
    "angry":    "#D00028",
    "fear":     "#AA00AA",
    "surprise": "#00A0DC",
    "disgust":  "#009678",
    "unknown":  "#787878",
}

# Dark-theme background colours
BG_FIGURE  = "#0D1117"
BG_AXES    = "#161B22"
C_GRID     = "#21262D"
C_SPINE    = "#30363D"
C_TEXT_PRI = "#E6EDF3"
C_TEXT_SEC = "#8B949E"
C_ACCENT   = "#00C8A0"


def _ecolor(emotion: str) -> str:
    return EMOTION_COLORS.get(emotion.lower(), "#787878")


def _style_ax(ax) -> None:
    """Apply consistent dark-theme styling to a matplotlib Axes."""
    ax.set_facecolor(BG_AXES)
    ax.tick_params(colors=C_TEXT_SEC, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(C_SPINE)
    ax.xaxis.label.set_color(C_TEXT_SEC)
    ax.yaxis.label.set_color(C_TEXT_SEC)
    ax.title.set_color(C_TEXT_PRI)


# ── Public API ────────────────────────────────────────────────────────────────

def print_summary() -> None:
    """Print a formatted session summary to stdout (ASCII-safe)."""
    history  = get_history()
    counts   = get_emotion_counts()
    dominant = get_dominant_emotion()
    duration = get_session_duration()
    mins, secs = divmod(int(duration), 60)

    sep = "=" * 60
    print("\n" + sep)
    print("   [SESSION SUMMARY] Emotion-Aware Interview Coach")
    print(sep)
    print(f"   Duration        : {mins:02d}m {secs:02d}s")
    print(f"   Total readings  : {len(history)}")
    print(f"   Dominant emotion: {dominant or 'N/A'}")

    if history:
        all_confs = [r["confidence"] for r in history]
        avg_all   = sum(all_confs) / len(all_confs)
        print(f"   Avg confidence  : {avg_all:.1f}%")

    print()
    print("   Emotion breakdown:")
    total = len(history) or 1
    for emotion, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct      = count / total * 100
        avg_conf = get_avg_confidence(emotion)
        bar      = "#" * int(pct / 5)
        print(f"   {emotion:<10}  {bar:<20}  {pct:5.1f}%  (avg conf {avg_conf:.1f}%)")
    print(sep + "\n")


def save_graph(output_dir: str = ".") -> str:
    """
    Generate and save a three-panel session analysis PNG.

    Panel 1  — Emotion timeline: coloured scatter dots (size = confidence)
                connected by a step line.
    Panel 2  — Frequency bar chart: reading count + % per emotion.
    Panel 3  — Average confidence per emotion: horizontal bar chart.

    Args:
        output_dir: Directory to write the PNG into (created if absent).

    Returns:
        Absolute path to the saved PNG, or '' if no data.
    """
    history = get_history()
    if not history:
        print("[Summary] No data to plot -- skipping graph.")
        return ""

    os.makedirs(output_dir, exist_ok=True)

    # ── Prepare data ──────────────────────────────────────────────────────────
    ALL_EMOTIONS = ["happy", "neutral", "sad", "angry", "fear", "surprise", "disgust", "unknown"]
    emo_idx      = {e: i for i, e in enumerate(ALL_EMOTIONS)}

    session_start = history[0]["timestamp"]
    times       = [(r["timestamp"] - session_start).total_seconds() for r in history]
    emo_vals    = [emo_idx.get(r["emotion"], len(ALL_EMOTIONS) - 1) for r in history]
    confidences = [r["confidence"] for r in history]
    dot_colors  = [_ecolor(r["emotion"]) for r in history]

    counts   = get_emotion_counts()
    dur_sec  = get_session_duration()
    mins, secs = divmod(int(dur_sec), 60)
    dominant = get_dominant_emotion() or "N/A"

    # Frequency + confidence data
    bar_emotions = sorted(counts.keys(), key=lambda e: -counts[e])
    bar_counts   = [counts[e] for e in bar_emotions]
    bar_colors   = [_ecolor(e) for e in bar_emotions]
    bar_confs    = [get_avg_confidence(e) for e in bar_emotions]
    total        = len(history) or 1

    # ── Figure ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(15, 9), facecolor=BG_FIGURE)
    gs  = gridspec.GridSpec(
        2, 2,
        height_ratios=[1.8, 1],
        width_ratios=[1.6, 1],
        hspace=0.50,
        wspace=0.35,
        left=0.07, right=0.97,
        top=0.90, bottom=0.08,
    )

    ax_timeline = fig.add_subplot(gs[0, :])   # full top row
    ax_freq     = fig.add_subplot(gs[1, 0])   # bottom-left
    ax_conf     = fig.add_subplot(gs[1, 1])   # bottom-right

    for ax in (ax_timeline, ax_freq, ax_conf):
        _style_ax(ax)

    # ── Supertitle ────────────────────────────────────────────────────────────
    fig.suptitle(
        f"Interview Session Report  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}  "
        f"|  {mins:02d}m {secs:02d}s  |  Dominant: {dominant.upper()}",
        color=C_TEXT_PRI,
        fontsize=12,
        fontweight="bold",
        y=0.96,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Panel 1 — Emotion timeline
    # ══════════════════════════════════════════════════════════════════════════
    ax_timeline.step(times, emo_vals, where="post",
                     color=C_SPINE, linewidth=1.0, zorder=1)

    ax_timeline.scatter(
        times, emo_vals,
        c=dot_colors,
        s=[max(25, c * 1.5) for c in confidences],
        edgecolors=BG_FIGURE,
        linewidths=0.5,
        zorder=2,
        alpha=0.90,
    )

    # Confidence value annotations (every ~8 readings to avoid clutter)
    step = max(1, len(history) // 8)
    for i in range(0, len(history), step):
        ax_timeline.annotate(
            f"{confidences[i]:.0f}%",
            xy=(times[i], emo_vals[i]),
            xytext=(0, 11),
            textcoords="offset points",
            ha="center",
            fontsize=6.5,
            color=C_TEXT_SEC,
        )

    # Y-axis: emotion names
    ax_timeline.set_yticks(range(len(ALL_EMOTIONS)))
    ax_timeline.set_yticklabels(
        [e.capitalize() for e in ALL_EMOTIONS],
        fontsize=8.5,
        color=C_TEXT_SEC,
    )
    ax_timeline.set_ylim(-0.6, len(ALL_EMOTIONS) - 0.4)
    ax_timeline.set_xlabel("Time (seconds)", fontsize=8.5)
    ax_timeline.set_title("Emotion Timeline  (dot size = confidence)",
                           fontsize=10, fontweight="bold", pad=8)
    ax_timeline.grid(axis="x", color=C_GRID, linestyle="--", linewidth=0.7)

    # Coloured legend patches
    from matplotlib.patches import Patch
    seen_emotions = list(dict.fromkeys(r["emotion"] for r in history))
    legend_handles = [
        Patch(facecolor=_ecolor(e), label=e.capitalize(), edgecolor=C_SPINE)
        for e in seen_emotions
    ]
    ax_timeline.legend(
        handles=legend_handles,
        loc="upper left",
        fontsize=7.5,
        framealpha=0.35,
        facecolor=BG_AXES,
        edgecolor=C_SPINE,
        labelcolor=C_TEXT_PRI,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Panel 2 — Frequency bar chart
    # ══════════════════════════════════════════════════════════════════════════
    bars = ax_freq.bar(
        bar_emotions,
        bar_counts,
        color=bar_colors,
        edgecolor=BG_FIGURE,
        linewidth=0.7,
        width=0.55,
    )

    for bar, count, conf in zip(bars, bar_counts, bar_confs):
        pct = count / total * 100
        ax_freq.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.1,
            f"{count} ({pct:.0f}%)\n{conf:.0f}% avg",
            ha="center", va="bottom",
            fontsize=7,
            color=C_TEXT_SEC,
        )

    ax_freq.set_title("Emotion Frequency", fontsize=9.5, fontweight="bold", pad=6)
    ax_freq.set_ylabel("Readings", fontsize=8)
    ax_freq.set_xticks(range(len(bar_emotions)))
    ax_freq.set_xticklabels(
        [e.capitalize() for e in bar_emotions],
        fontsize=8, color=C_TEXT_SEC,
    )
    ax_freq.set_ylim(0, max(bar_counts) * 1.40 if bar_counts else 1)
    ax_freq.grid(axis="y", color=C_GRID, linestyle="--", linewidth=0.7)

    # ══════════════════════════════════════════════════════════════════════════
    # Panel 3 — Average confidence per emotion (horizontal bars)
    # ══════════════════════════════════════════════════════════════════════════
    h_labels = [e.capitalize() for e in bar_emotions]
    h_confs  = bar_confs
    h_colors = bar_colors

    h_bars = ax_conf.barh(
        h_labels,
        h_confs,
        color=h_colors,
        edgecolor=BG_FIGURE,
        linewidth=0.7,
        height=0.50,
    )

    for bar, conf in zip(h_bars, h_confs):
        ax_conf.text(
            conf + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{conf:.1f}%",
            va="center",
            fontsize=7.5,
            color=C_TEXT_PRI,
        )

    ax_conf.set_title("Avg Confidence per Emotion", fontsize=9.5, fontweight="bold", pad=6)
    ax_conf.set_xlabel("Confidence (%)", fontsize=8)
    ax_conf.set_xlim(0, 105)
    ax_conf.grid(axis="x", color=C_GRID, linestyle="--", linewidth=0.7)
    ax_conf.invert_yaxis()   # highest first

    # ── Save ──────────────────────────────────────────────────────────────────
    ts    = (_session_start or datetime.now()).strftime("%Y%m%d_%H%M%S")
    fname = f"emotion_graph_{ts}.png"
    fpath = os.path.join(output_dir, fname)

    plt.savefig(fpath, dpi=150, bbox_inches="tight", facecolor=BG_FIGURE)
    plt.close(fig)
    print(f"[Summary] Emotion graph saved -> {fpath}")
    return fpath


def generate_report_payload(session_info: dict, question_history: list) -> dict:
    """
    Compiles full performance metrics, composure trends, and roadmap steps into a
    dictionary for the browser UI post-session report page.
    """
    history = get_history()
    duration = get_session_duration()
    dominant = get_dominant_emotion() or "neutral"
    
    # 1. Composure Score from history (happy/neutral are high composure)
    composure_weights = {
        "happy": 100,
        "neutral": 100,
        "surprise": 80,
        "sad": 60,
        "disgust": 60,
        "angry": 40,
        "fear": 40,
        "unknown": 70
    }
    
    if history:
        comp_scores = [composure_weights.get(r["emotion"].lower(), 70) for r in history]
        composure_score = sum(comp_scores) / len(comp_scores)
    else:
        composure_score = 80.0
        
    # Composure history array for drawing report chart (sample down to 50 items)
    raw_comp_history = [composure_weights.get(r["emotion"].lower(), 70) for r in history]
    if len(raw_comp_history) > 50:
        indices = np.linspace(0, len(raw_comp_history) - 1, 50, dtype=int)
        composure_history = [raw_comp_history[i] for i in indices]
    else:
        composure_history = raw_comp_history if raw_comp_history else [80, 80]
        
    # Calculate Emotion Distribution
    counts = get_emotion_counts()
    total_readings = sum(counts.values()) or 1
    emotion_dist = {emo: round((count / total_readings) * 100, 1) for emo, count in counts.items()}
        
    # 2. Confidence Score from average DeepFace dominant confidences
    if history:
        conf_score = sum(r["confidence"] for r in history) / len(history)
    else:
        conf_score = 75.0
        
    # 3. Eye Contact Score
    eye_contact_score = session_info.get("eye_contact_score", 85.0)
    
    # 4. Speaking Pace and Fillers
    pace = session_info.get("speech", {}).get("pace_wpm", 130.0)
    fillers = session_info.get("speech", {}).get("filler_words", 0)
    
    # 5. Communication Score: Deduct points for WPM pace deviations and filler words
    pace_diff = abs(pace - 135.0)
    comm_score = 100.0 - (pace_diff * 1.2) - (fillers * 4.0)
    comm_score = max(50.0, min(100.0, comm_score))
    
    # 6. Overall Score
    overall_score = (composure_score * 0.40) + (comm_score * 0.35) + (eye_contact_score * 0.25)
    overall_score = max(40.0, min(100.0, overall_score))
    
    # Calculate Question Breakdown and Composure scores per question
    q_breakdown = []
    strongest_q = None
    weakest_q = None
    max_q_comp = -1.0
    min_q_comp = 101.0
    
    for idx, q in enumerate(question_history):
        q_emotions = q.get("emotions", [])
        if q_emotions:
            q_dom = max(set(q_emotions), key=q_emotions.count)
            q_comp_score = sum(composure_weights.get(e.lower(), 70) for e in q_emotions) / len(q_emotions)
        else:
            q_dom = "neutral"
            q_comp_score = 80.0
            
        coaching_notes = "Maintained good engagement."
        if q_dom in ["fear", "sad", "surprise"]:
            coaching_notes = "Nervousness detected. Focus on pacing and breathe deeply during transitions."
        elif q_dom in ["happy", "neutral"]:
            coaching_notes = "Excellent composure. Approached the topic with confidence and calm."
        elif q_dom == "angry":
            coaching_notes = "Some facial tension. Keep jaw relaxed and voice steady."
            
        q_data = {
            "category": q.get("category", "Intro"),
            "question": q.get("question", ""),
            "emotion": q_dom,
            "coaching_notes": coaching_notes,
            "pace_wpm": round(q.get("pace_wpm", 130.0), 1),
            "filler_words": int(q.get("filler_words", 0)),
            "response_time": round(q.get("response_time", 0.0), 1),
            "composure_score": round(q_comp_score, 1)
        }
        q_breakdown.append(q_data)
        
        # Track strongest and weakest answers based on composure
        if q_comp_score > max_q_comp:
            max_q_comp = q_comp_score
            strongest_q = q_data
        if q_comp_score < min_q_comp:
            min_q_comp = q_comp_score
            weakest_q = q_data

    # Formatting text indicators for strongest/weakest answers
    if not strongest_q:
        strongest_answer = "No responses logged."
    else:
        strongest_answer = f"Question #{question_history.index(next(x for x in question_history if x['question'] == strongest_q['question'])) + 1} ({strongest_q['category']}): \"{strongest_q['question']}\" — You demonstrated excellent stability and composure."
        
    if not weakest_q:
        weakest_answer = "No responses logged."
    else:
        weakest_answer = f"Question #{question_history.index(next(x for x in question_history if x['question'] == weakest_q['question'])) + 1} ({weakest_q['category']}): \"{weakest_q['question']}\" — Signs of visual distress or nervousness were detected; focus on breathing exercises here."

    # 7. Strengths, Weaknesses, Roadmap compile
    strengths = []
    weaknesses = []
    roadmap = []
    
    if composure_score >= 80:
        strengths.append("Exhibited excellent composure and emotional stability under questioning.")
    else:
        weaknesses.append("Showed signs of tension or nervousness under pressure. Focus on deep breathing.")
        
    if eye_contact_score >= 80:
        strengths.append("Maintained strong, consistent virtual eye contact with the camera.")
    else:
        weaknesses.append("Frequent loss of camera contact. Look directly at the lens, not the screen.")
        
    if comm_score >= 80:
        strengths.append("Communicated clearly with an appropriate speaking pace.")
    else:
        if pace > 145:
            weaknesses.append("Speaking pace was slightly rushed, making it harder to absorb key points.")
        elif pace < 115:
            weaknesses.append("Speaking pace was a bit slow. Try to speak with more energy.")
        
        if fillers > 3:
            weaknesses.append(f"High usage of filler words ({fillers} fillers logged). Practice insertion of structured pauses.")
            
    if fillers <= 2:
        strengths.append("Spoke confidently with minimal use of filler words.")
        
    if not strengths:
        strengths.append("Successfully answered all interview stage questions.")
        strengths.append("Showed strong commitment to engaging with the interviewer.")
        
    # Roadmap items
    if composure_score < 80 or dominant in ["fear", "sad", "angry"]:
        roadmap.append("Practice box-breathing (inhale 4s, hold 4s, exhale 4s, hold 4s) to stabilize composure under stress.")
    else:
        roadmap.append("Maintain positive composure; practice adding subtle smiles to appear warm and approachable.")
        
    if fillers > 2:
        roadmap.append("Apply the 'Pause Technique': insert a silent 1-second pause when searching for words instead of vocalizing fillers.")
    else:
        roadmap.append("Continue to speak clearly; try filming yourself to diversify your technical vocabulary.")
        
    if eye_contact_score < 80:
        roadmap.append("Position your practice window directly below your webcam lens to capture a natural eye line.")
    else:
        roadmap.append("Practice virtual eye contact while articulating transition points so it stays consistent.")
        
    roadmap.append("Structure answers using the STAR method (Situation, Task, Action, Result) for behavioral questions.")
    
    if not q_breakdown:
        q_breakdown = [{
            "category": session_info.get("stage_name", "Intro"),
            "question": session_info.get("q_text", "Tell me about yourself."),
            "emotion": dominant,
            "coaching_notes": "Session summary generated.",
            "pace_wpm": round(pace, 1),
            "filler_words": int(fillers),
            "response_time": 0.0,
            "composure_score": 80.0
        }]
        
    return {
        "overall_score": round(overall_score, 1),
        "communication_score": round(comm_score, 1),
        "confidence_score": round(conf_score, 1),
        "eye_contact_score": round(eye_contact_score, 1),
        "average_pace_wpm": round(pace, 1),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "roadmap": roadmap,
        "question_breakdown": q_breakdown,
        "duration_sec": round(duration, 1),
        "composure_history": composure_history,
        "emotion_distribution": emotion_dist,
        "strongest_answer": strongest_answer,
        "weakest_answer": weakest_answer
    }

