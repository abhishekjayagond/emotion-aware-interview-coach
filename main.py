"""
main.py
-------
Emotion-Aware Virtual Interview Coach  —  v6 (High Density Analytics)
=====================================================================
Entry point. Ties together the conversational state machine and rich AI HUD.
"""

import argparse
import sys
import time
import random
import cv2
import numpy as np

from emotion_detector import analyze_emotion
from coach import get_coaching
from display import (
    apply_cinematic_vignette,
    draw_face_box,
    draw_analytics_sidebar,
    draw_top_hud,
    draw_audio_hud,
    draw_interview_card,
    draw_session_summary,
    draw_status,
)
import session_logger as logger
import session_summary as summary
from interview_questions import STAGES, get_question_for_stage, get_follow_up
from webcam_handler import detect_source, open_source

# ── Configuration ──────────────────────────────────────────────────────────────
WINDOW_TITLE    = "AI Interview Assistant"
ANALYZE_EVERY_N = 5
LOG_DIR         = "session_logs"


class InterviewSessionManager:
    """Manages the state machine of the conversational interview flow."""
    def __init__(self):
        self.stage_idx = 0
        self.q_count = 1
        self.state = "GENERATING"
        self.state_start = time.time()
        self.current_q = ("", "")
        self.last_emotion = "neutral"
        self.difficulty = "Adaptive (Stable)"
        self.speech = {
            "pace_wpm": 130.0,
            "filler_words": 0,
            "response_time": 0.0
        }
        self.advance_question()
        
    def advance_question(self):
        if self.stage_idx < len(STAGES):
            self.current_q = get_question_for_stage(STAGES[self.stage_idx], self.last_emotion)
            self.stage_idx += 1
        else:
            self.current_q = ("Wrap-up", "Thank you for your time. The interview is now complete.")
            
        self.state = "GENERATING"
        self.state_start = time.time()
        self.q_count += 1
        
    def update(self, current_emotion):
        self.last_emotion = current_emotion
        elapsed = time.time() - self.state_start
        
        # State transitions
        if self.state == "GENERATING" and elapsed > 2.5:
            self.state = "LISTENING"
            self.state_start = time.time()
            self.speech["response_time"] = 0.0
            
        elif self.state == "LISTENING":
            self.speech["response_time"] = elapsed
            
            # Simulate speech heuristics
            if random.random() < 0.01:  # Occasional filler word
                self.speech["filler_words"] += 1
            
            # Simulate pace fluctuation (reverting gently to 130)
            self.speech["pace_wpm"] += random.uniform(-1.5, 1.5)
            self.speech["pace_wpm"] = max(110.0, min(self.speech["pace_wpm"], 160.0))
            if self.speech["pace_wpm"] > 145.0: self.speech["pace_wpm"] -= 0.5
            elif self.speech["pace_wpm"] < 120.0: self.speech["pace_wpm"] += 0.5
            
            if elapsed > 15.0:  # 15s per question in demo
                if self.stage_idx > len(STAGES):
                    pass # Stay in wrap up
                else:
                    self.state = "ANALYZING"
                    self.state_start = time.time()
            
        elif self.state == "ANALYZING" and elapsed > 2.5:
            # 30% chance for a dynamic follow-up
            if random.random() < 0.3 and self.stage_idx <= len(STAGES):
                self.current_q = get_follow_up(current_emotion)
                self.state = "GENERATING"
                self.state_start = time.time()
                self.q_count += 1
            else:
                self.advance_question()
                
    def get_elapsed_in_state(self):
        return time.time() - self.state_start


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", "-s", default=None)
    parser.add_argument("--demo", "-d", action="store_true")
    parser.add_argument("--timeout", "-t", type=float, default=4.0)
    parser.add_argument("--no-fallback", action="store_true")
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    if args.demo:
        from webcam_handler import SourceInfo
        source_info = SourceInfo("demo", None, None, True, "Demo Mode")
    else:
        source_info = detect_source(args.source, args.timeout, not args.no_fallback)

    if source_info.kind == "none":
        sys.exit(1)

    logger.start_session()
    
    frame_count = 0
    last_result = None
    session_manager = InterviewSessionManager()
    show_summary = False

    try:
        for frame in open_source(source_info):
            frame_count += 1

            # Portrait frame handling
            h, w = frame.shape[:2]
            if h > w:
                target_w = int(h * 1.5)
                bg = cv2.resize(frame, (target_w, h))
                bg = cv2.GaussianBlur(bg, (99, 99), 0)
                bg = cv2.addWeighted(bg, 0.7, np.zeros_like(bg), 0.3, 0)
                x = (target_w - w) // 2
                bg[0:h, x:x+w] = frame
                frame = bg

            # DeepFace inference
            if frame_count % ANALYZE_EVERY_N == 0:
                result = analyze_emotion(frame)
                if result is not None:
                    last_result = result
                    logger.log_emotion(result["emotion"], result["scores"])

            # Update interview state machine
            current_emo = last_result["emotion"] if last_result else "neutral"
            session_manager.update(current_emo)

            # Gather Data
            history = logger.get_history()
            session_elapsed = logger.get_session_duration()
            q_category, q_text = session_manager.current_q
            
            stage_name = STAGES[session_manager.stage_idx-1] if session_manager.stage_idx > 0 and session_manager.stage_idx <= len(STAGES) else "Wrap-up"
            
            session_info = {
                "stage_name": stage_name,
                "stage_idx": min(session_manager.stage_idx, len(STAGES)),
                "total_stages": len(STAGES),
                "q_count": session_manager.q_count,
                "state": session_manager.state,
                "state_elapsed": session_manager.get_elapsed_in_state(),
                "elapsed": session_elapsed,
                "difficulty": session_manager.difficulty,
                "speech": session_manager.speech
            }

            # ── Draw Overlays ──
            apply_cinematic_vignette(frame, intensity=0.45)

            if show_summary:
                draw_session_summary(frame, session_info, history)
                cv2.imshow(WINDOW_TITLE, frame)
                delay = 30 if source_info.kind == "image" else 1
                key = cv2.waitKey(delay) & 0xFF
                if key in (ord("q"), ord("Q"), 13):  # 13 is Enter
                    break
                continue

            draw_top_hud(frame, session_info)

            if last_result:
                emotion    = last_result["emotion"]
                region     = last_result["region"]
                confidence = last_result["scores"].get(emotion, 0.0)
                coaching   = get_coaching(emotion)

                # Adaptive difficulty heuristic logic based on emotion
                if emotion in ["fear", "sad", "surprise"]:
                    session_manager.difficulty = "Adaptive (Easing...)"
                elif emotion in ["happy", "neutral"]:
                    session_manager.difficulty = "Adaptive (Stable)"

                draw_face_box(frame, region, coaching["color"])
                draw_analytics_sidebar(frame, emotion, confidence, history, session_info)
                draw_audio_hud(frame, session_info)
                draw_interview_card(frame, q_text, coaching["tip"], session_info)
            else:
                draw_status(frame, "Calibrating sensors...")

            cv2.imshow(WINDOW_TITLE, frame)
            
            delay = 30 if source_info.kind == "image" else 1
            if cv2.waitKey(delay) & 0xFF in (ord("q"), ord("Q")):
                show_summary = True

    except KeyboardInterrupt:
        pass

    cv2.destroyAllWindows()
    summary.print_summary()
    logger.save_csv(output_dir=LOG_DIR)
    summary.save_graph(output_dir=LOG_DIR)


if __name__ == "__main__":
    main()
