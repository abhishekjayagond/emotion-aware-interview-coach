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
