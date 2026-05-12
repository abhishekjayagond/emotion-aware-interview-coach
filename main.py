"""
main.py
-------
Emotion-Aware Virtual Interview Coach  —  v4
=============================================
Entry point. Ties together:
  • Source detection with timeout  (webcam_handler.py)
  • DeepFace emotion analysis      (emotion_detector.py)
  • Coaching tips                  (coach.py)
  • OpenCV overlays                (display.py)
  • Session logging + CSV export   (session_logger.py)
  • Matplotlib emotion graph       (session_summary.py)
  • Random interview questions     (interview_questions.py)

Usage
-----
  python main.py                         # Auto-detect webcam -> demo fallback
  python main.py --demo                  # Force demo mode (no camera needed)
  python main.py --source path/to.mp4    # Analyse a pre-recorded video
  python main.py --source path/to.jpg    # Analyse a single image file
  python main.py --source 1              # Use camera index 1 explicitly
  python main.py --timeout 8             # Wait up to 8 s per camera index

Press Q (or close the window) to quit.

Outputs written to session_logs/
  session_<TIMESTAMP>.csv
  emotion_graph_<TIMESTAMP>.png
"""

import argparse
import sys

import cv2

from emotion_detector import analyze_emotion
from coach import get_coaching
from display import (
    draw_face_box,
    draw_emotion_label,
    draw_tip_banner,
    draw_quit_hint,
    draw_status,
    draw_analytics_sidebar,
    draw_timeline_bar,
    draw_question_banner,
    draw_source_tag,
)
import session_logger as logger
import session_summary as summary
from interview_questions import get_random_question
from webcam_handler import detect_source, open_source


# ── Configuration ──────────────────────────────────────────────────────────────
WINDOW_TITLE      = "Emotion-Aware Interview Coach"
ANALYZE_EVERY_N   = 5     # Run DeepFace every N frames (keeps feed smooth)
QUESTION_CHANGE_N = 150   # Rotate question every N frames (~5 s at 30 fps)
LOG_DIR           = "session_logs"


# ── CLI argument parser ────────────────────────────────────────────────────────
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Emotion-Aware Virtual Interview Coach",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                         Auto-detect webcam, demo if none found
  python main.py --demo                  Force demo mode (no camera required)
  python main.py --source interview.mp4  Analyse a pre-recorded video
  python main.py --source photo.jpg      Analyse a static image
  python main.py --source 1              Use camera index 1
  python main.py --timeout 8             Wait 8 s per camera index
        """,
    )
    parser.add_argument(
        "--source", "-s",
        metavar="PATH_OR_INDEX",
        default=None,
        help="Video file, image file, or camera index (default: auto-detect).",
    )
    parser.add_argument(
        "--demo", "-d",
        action="store_true",
        default=False,
        help="Force demo mode -- run with a synthetic animated face.",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=4.0,
        metavar="SECONDS",
        help="Seconds to wait per camera index before giving up (default: 4).",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        default=False,
        help="Exit instead of falling back to demo mode when no camera found.",
    )
    return parser


# ── Mode banner ────────────────────────────────────────────────────────────────
def _print_mode_banner(description: str) -> None:
    """Print a clear startup banner showing which source is in use."""
    sep = "=" * 55
    print(sep)
    print(f"  Emotion-Aware Interview Coach  |  {description}")
    print(sep)


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    args = _build_parser().parse_args()

    # ── Determine source ───────────────────────────────────────────────────────
    if args.demo:
        from webcam_handler import SourceInfo
        source_info = SourceInfo(
            kind="demo",
            path=None,
            cap=None,
            is_live=True,
            description="Demo Mode (forced)",
        )
    else:
        source_info = detect_source(
            source=args.source,
            timeout_s=args.timeout,
            demo_fallback=not args.no_fallback,
        )

    if source_info.kind == "none":
        print("[ERROR] No valid source available. Exiting.")
        print("        Tip: run with --demo to use demo mode, or")
        print("             pass --source <file> to analyse a video/image.")
        sys.exit(1)

    _print_mode_banner(source_info.description)

    # ── Start session ──────────────────────────────────────────────────────────
    logger.start_session()

    print(f"[INFO] Source: {source_info.description}")
    if source_info.is_live:
        print("[INFO] Press Q to quit.")
    else:
        print("[INFO] Press Q to quit early, or wait for the source to finish.")
    print("[INFO] DeepFace will warm up on the first few frames -- this is normal.\n")

    frame_count      = 0
    last_result      = None
    current_question = get_random_question()

    # ── Frame loop ─────────────────────────────────────────────────────────────
    try:
        for frame in open_source(source_info):
            frame_count += 1

            # Rotate interview question periodically
            if frame_count % QUESTION_CHANGE_N == 0:
                current_question = get_random_question()

            # Emotion analysis every N frames
            if frame_count % ANALYZE_EVERY_N == 0:
                result = analyze_emotion(frame)
                if result is not None:
                    last_result = result
                    logger.log_emotion(result["emotion"], result["scores"])

            # Gather session state for analytics sidebar
            history    = logger.get_history()
            elapsed    = logger.get_session_duration()

            # ── Draw overlays (order matters — back to front) ──────────────────

            # 1. Timeline bar at top
            draw_timeline_bar(frame, history)

            # 2. Face box + emotion label (on the video feed itself)
            if last_result:
                emotion    = last_result["emotion"]
                region     = last_result["region"]
                scores     = last_result["scores"]
                coaching   = get_coaching(emotion)
                color      = coaching["color"]
                confidence = scores.get(emotion, 0.0)

                draw_face_box(frame, region, color)
                draw_emotion_label(frame, coaching["label"], region, color)

                # 3. Live analytics sidebar (right panel)
                draw_analytics_sidebar(
                    frame, emotion, confidence, history, elapsed
                )

                # 4. Question strip + tip banner (bottom)
                draw_question_banner(frame, *current_question)
                draw_tip_banner(frame, coaching["tip"], color)

            else:
                # Still warming up / no face found yet
                draw_status(frame, "Looking for your face...")

            # 5. HUD chrome
            draw_quit_hint(frame)
            draw_source_tag(frame, source_info.description)

            cv2.imshow(WINDOW_TITLE, frame)

            # Wait longer for static images so they don't flash by
            delay = 30 if source_info.kind == "image" else 1
            key = cv2.waitKey(delay) & 0xFF
            if key in (ord("q"), ord("Q")):
                break

    except ValueError as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")

    # ── Cleanup ────────────────────────────────────────────────────────────────
    cv2.destroyAllWindows()
    print("[INFO] Session ended. Generating report...\n")

    summary.print_summary()
    logger.save_csv(output_dir=LOG_DIR)
    summary.save_graph(output_dir=LOG_DIR)

    print("[INFO] Good luck with your interview!")


if __name__ == "__main__":
    main()
