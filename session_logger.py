"""
session_logger.py
-----------------
Handles all data-logging concerns for an interview session:
  • In-memory emotion history (list of timestamped records)
  • CSV export with timestamps on session end

Each record stores:
    timestamp   – wall-clock time of the analysis
    emotion     – dominant emotion string
    confidence  – score of the dominant emotion (0-100)
    all_scores  – JSON-serialised dict of every emotion score
"""

import csv
import json
import os
from datetime import datetime


# ── Session state ─────────────────────────────────────────────────────────────
_history: list[dict] = []          # [{timestamp, emotion, confidence, scores}]
_session_start: datetime | None = None


# ── Public API ────────────────────────────────────────────────────────────────

def start_session() -> None:
    """Reset history and record the session start time."""
    global _history, _session_start
    _history = []
    _session_start = datetime.now()
    print(f"[Logger] Session started at {_session_start.strftime('%H:%M:%S')}")


def log_emotion(emotion: str, scores: dict) -> None:
    """
    Append one emotion reading to the in-memory history.

    Args:
        emotion: Dominant emotion string (e.g. 'happy').
        scores:  Full emotion-score dict from DeepFace (values 0-100).
    """
    confidence = round(scores.get(emotion, 0.0), 1)
    record = {
        "timestamp": datetime.now(),
        "emotion":   emotion,
        "confidence": confidence,
        "scores":    scores,
    }
    _history.append(record)


def get_history() -> list[dict]:
    """Return the complete in-memory history list (read-only view)."""
    return list(_history)


def get_emotion_counts() -> dict[str, int]:
    """Return a {emotion: count} tally across the full session."""
    counts: dict[str, int] = {}
    for rec in _history:
        counts[rec["emotion"]] = counts.get(rec["emotion"], 0) + 1
    return counts


def get_dominant_emotion() -> str | None:
    """Return the most-seen emotion across the session, or None if empty."""
    counts = get_emotion_counts()
    return max(counts, key=counts.get) if counts else None


def get_avg_confidence(emotion: str) -> float:
    """Average confidence score for a specific emotion across its readings."""
    values = [r["confidence"] for r in _history if r["emotion"] == emotion]
    return round(sum(values) / len(values), 1) if values else 0.0


def get_session_duration() -> float:
    """Return total session length in seconds (0 if session never started)."""
    if _session_start is None:
        return 0.0
    return (datetime.now() - _session_start).total_seconds()


def save_csv(output_dir: str = ".") -> str:
    """
    Write the session history to a timestamped CSV file.

    Args:
        output_dir: Directory to write the CSV into (created if absent).

    Returns:
        Absolute path to the written CSV file.
    """
    os.makedirs(output_dir, exist_ok=True)
    fname = f"session_{_session_start.strftime('%Y%m%d_%H%M%S')}.csv"
    fpath = os.path.join(output_dir, fname)

    with open(fpath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "emotion", "confidence_pct", "all_scores_json"])
        for rec in _history:
            writer.writerow([
                rec["timestamp"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                rec["emotion"],
                rec["confidence"],
                json.dumps({k: round(v, 2) for k, v in rec["scores"].items()}),
            ])

    print(f"[Logger] CSV saved -> {fpath}")
    return fpath
