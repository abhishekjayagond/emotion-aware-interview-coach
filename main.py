"""
main.py
-------
Emotion-Aware Virtual Interview Coach  —  Redesigned v7 (Modern Desktop Interface)
==================================================================================
Entry point. Spawns a background HTTP server and runs the camera loop headlessly.
Communicates frame buffers and state updates to the browser interface.
"""

import argparse
import sys
import time
import random
import cv2
import numpy as np
import webbrowser

from emotion_detector import analyze_emotion
from coach import get_coaching
import web_server
import session_logger as logger
import session_summary as summary
from interview_questions import STAGES, get_question_for_stage, get_follow_up
from webcam_handler import detect_source, open_source

# ── Configuration ──────────────────────────────────────────────────────────────
WINDOW_TITLE    = "AI Interview Assistant"
ANALYZE_EVERY_N = 5
LOG_DIR         = "session_logs"
PORT            = 8000


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
        
        # Audio/Speech heuristics state
        self.speech = {
            "pace_wpm": 130.0,
            "filler_words": 0,
            "response_time": 0.0
        }
        
        # Track composure score
        self.composure_score = 100.0
        
        # Advanced history trackers for navigation & reporting
        self.asked_questions = []
        self.current_asked_idx = -1
        self.emotions_by_q_idx = {}
        self.speech_by_q_idx = {}
        
        # Probe metrics for Eye Contact percentage
        self.total_probes = 0
        self.successful_probes = 0
        
        self.advance_question()
        
    def record_current_q_metrics(self):
        if self.current_asked_idx >= 0:
            total_fillers_before = sum(self.speech_by_q_idx.get(i, {"filler_words": 0})["filler_words"] for i in range(self.current_asked_idx))
            q_fillers = self.speech["filler_words"] - total_fillers_before
            q_fillers = max(0, q_fillers)
            
            self.speech_by_q_idx[self.current_asked_idx] = {
                "pace_wpm": self.speech["pace_wpm"],
                "filler_words": q_fillers,
                "response_time": self.speech["response_time"]
            }

    def advance_question(self):
        self.record_current_q_metrics()
        # If we are navigating history and click next, resume the next pre-generated question
        if self.current_asked_idx < len(self.asked_questions) - 1:
            self.current_asked_idx += 1
            self.current_q = self.asked_questions[self.current_asked_idx]
            self.state = "GENERATING"
            self.state_start = time.time()
            self.q_count = self.current_asked_idx + 1
            return

        # Generate a new question
        if self.stage_idx < len(STAGES):
            q_cat, q_text = get_question_for_stage(STAGES[self.stage_idx], self.last_emotion)
            self.stage_idx += 1
        else:
            q_cat, q_text = ("Wrap-up", "Thank you for your time. The interview is now complete.")
            
        self.current_q = (q_cat, q_text)
        self.asked_questions.append((q_cat, q_text))
        self.current_asked_idx = len(self.asked_questions) - 1
        
        self.state = "GENERATING"
        self.state_start = time.time()
        self.q_count = self.current_asked_idx + 1
        
    def previous_question(self):
        self.record_current_q_metrics()
        if self.current_asked_idx > 0:
            self.current_asked_idx -= 1
            self.current_q = self.asked_questions[self.current_asked_idx]
            self.state = "LISTENING"
            self.state_start = time.time()
            self.q_count = self.current_asked_idx + 1

    def update(self, current_emotion):
        if self.state == "PAUSED":
            return
        self.last_emotion = current_emotion
        elapsed = time.time() - self.state_start
        
        # Log emotion in current question bucket
        if self.current_asked_idx >= 0:
            self.emotions_by_q_idx.setdefault(self.current_asked_idx, []).append(current_emotion)
        
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
            
            if elapsed > 15.0:  # 15s per question in demo/hands-free mode
                if self.stage_idx > len(STAGES):
                    pass # Stay in wrap up
                else:
                    self.state = "ANALYZING"
                    self.state_start = time.time()
            
        elif self.state == "ANALYZING" and elapsed > 2.5:
            # 30% chance for a dynamic follow-up
            if random.random() < 0.3 and self.stage_idx <= len(STAGES):
                q_cat, q_text = get_follow_up(current_emotion)
                self.current_q = (q_cat, q_text)
                self.asked_questions.append((q_cat, q_text))
                self.current_asked_idx = len(self.asked_questions) - 1
                self.state = "GENERATING"
                self.state_start = time.time()
                self.q_count = self.current_asked_idx + 1
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
    
    # Spin up web server background thread
    server = web_server.start_server(port=PORT)
    webbrowser.open(f"http://localhost:{PORT}")
    
    frame_count = 0
    last_result = None
    session_manager = InterviewSessionManager()
    show_summary = False
    
    # Set initial server states
    web_server.set_report_data({})
    web_server.update_state({"state": "CALIBRATING", "elapsed": 0})

    try:
        # Loop on frame inputs
        for frame in open_source(source_info):
            # Check for API control actions from web frontend
            action = web_server.get_next_action()
            if action == "exit":
                break
            elif action == "restart":
                print("[Session] Restarting interview session...")
                logger.start_session()
                session_manager = InterviewSessionManager()
                show_summary = False
                web_server.set_report_data({})
                web_server.update_state({"state": "CALIBRATING", "elapsed": 0})
            elif action == "pause":
                if session_manager.state != "PAUSED":
                    print("[Session] Interview paused.")
                    session_manager.pre_paused_state = session_manager.state
                    session_manager.state = "PAUSED"
                    session_manager.paused_time_start = time.time()
                else:
                    paused_duration = time.time() - session_manager.paused_time_start
                    print(f"[Session] Interview resumed. Paused duration: {paused_duration:.1f}s")
                    session_manager.state = session_manager.pre_paused_state
                    session_manager.state_start += paused_duration
                    logger.add_paused_time(paused_duration)
            elif action == "next":
                print("[Session] Manual next question action.")
                if session_manager.state == "PAUSED":
                    session_manager.state = session_manager.pre_paused_state
                    paused_duration = time.time() - session_manager.paused_time_start
                    session_manager.state_start += paused_duration
                    logger.add_paused_time(paused_duration)
                session_manager.advance_question()
            elif action == "prev":
                print("[Session] Manual previous question action.")
                if session_manager.state == "PAUSED":
                    session_manager.state = session_manager.pre_paused_state
                    paused_duration = time.time() - session_manager.paused_time_start
                    session_manager.state_start += paused_duration
                    logger.add_paused_time(paused_duration)
                session_manager.previous_question()
            elif action == "finish":
                print("[Session] Session finished by client request.")
                if session_manager.state == "PAUSED":
                    session_manager.state = session_manager.pre_paused_state
                    paused_duration = time.time() - session_manager.paused_time_start
                    logger.add_paused_time(paused_duration)
                show_summary = True

            # If showing report, we enter an idle CPU-saving state
            if show_summary:
                # Compile final report summary
                session_manager.record_current_q_metrics()
                q_hist = []
                for idx, (cat, text) in enumerate(session_manager.asked_questions):
                    q_speech = session_manager.speech_by_q_idx.get(idx, {
                        "pace_wpm": 130.0,
                        "filler_words": 0,
                        "response_time": 0.0
                    })
                    q_hist.append({
                        "category": cat,
                        "question": text,
                        "emotions": session_manager.emotions_by_q_idx.get(idx, []),
                        "pace_wpm": q_speech["pace_wpm"],
                        "filler_words": q_speech["filler_words"],
                        "response_time": q_speech["response_time"]
                    })
                
                # Eye contact percentage calculation
                eye_contact_score = (session_manager.successful_probes / max(1, session_manager.total_probes)) * 100
                session_info = {
                    "stage_name": "Summary",
                    "stage_idx": len(STAGES),
                    "total_stages": len(STAGES),
                    "speech": session_manager.speech,
                    "eye_contact_score": eye_contact_score
                }
                
                report = summary.generate_report_payload(session_info, q_hist)
                web_server.set_report_data(report)
                
                # Push showing summary flag to clients
                web_server.update_state({"show_summary": True})
                time.sleep(0.2)
                continue

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
                h, w = frame.shape[:2]

            # DeepFace inference (skip if paused)
            is_paused = (session_manager.state == "PAUSED")
            is_probe_frame = (frame_count % ANALYZE_EVERY_N == 0)
            if is_probe_frame and not is_paused:
                session_manager.total_probes += 1
                result = analyze_emotion(frame)
                if result is not None:
                    session_manager.successful_probes += 1
                    last_result = result
                    logger.log_emotion(result["emotion"], result["scores"])

            # Update interview state machine
            current_emo = last_result["emotion"] if last_result else "neutral"
            session_manager.update(current_emo)

            # Gather State Data
            history = logger.get_history()
            session_elapsed = logger.get_session_duration()
            q_category, q_text = session_manager.current_q
            
            # Map current question category to index
            try:
                stage_idx = STAGES.index(q_category) + 1
            except ValueError:
                stage_idx = len(STAGES)
            
            # Calculate Composure Score
            target_composure = 100.0
            if history:
                recent = history[-15:]
                nervous = [r["scores"].get("fear", 0.0) + r["scores"].get("sad", 0.0) for r in recent]
                if nervous:
                    target_composure = max(0.0, 100.0 - sum(nervous)/len(nervous))
            session_manager.composure_score = session_manager.composure_score * 0.9 + target_composure * 0.1

            # Get coaching feedback tip
            coaching = get_coaching(current_emo)

            # Adaptive difficulty heuristic logic based on emotion
            if current_emo in ["fear", "sad", "surprise"]:
                session_manager.difficulty = "Adaptive (Easing...)"
            elif current_emo in ["happy", "neutral"]:
                session_manager.difficulty = "Adaptive (Stable)"

            # Eye contact ratio
            eye_contact_score = (session_manager.successful_probes / max(1, session_manager.total_probes)) * 100

            # Compile Web State Payload
            state_payload = {
                "stage_name": q_category,
                "stage_idx": stage_idx,
                "total_stages": len(STAGES),
                "q_count": session_manager.q_count,
                "q_text": q_text,
                "state": session_manager.state,
                "state_elapsed": session_manager.get_elapsed_in_state(),
                "elapsed": session_elapsed,
                "difficulty": session_manager.difficulty,
                "speech": session_manager.speech,
                "emotion": current_emo,
                "emotion_confidence": last_result["scores"].get(current_emo, 0.0) if last_result else 0.0,
                "emotion_color": f"rgb({coaching['color'][2]}, {coaching['color'][1]}, {coaching['color'][0]})",  # Convert BGR to RGB
                "coaching_tip": coaching["tip"],
                "region": last_result["region"] if (last_result and is_probe_frame and not is_paused) else (last_result["region"] if (last_result and not is_paused) else None),
                "frame_width": w,
                "frame_height": h,
                "composure_score": session_manager.composure_score,
                "eye_contact_score": eye_contact_score,
                "is_paused": is_paused,
                "show_summary": False
            }

            # Update server state and JPEG frame buffer
            web_server.update_state(state_payload)
            
            # Draw visual guides (if any) and compress to JPEG for streaming
            # Compress BGR frame to JPEG format
            ret, jpeg_buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ret:
                web_server.set_latest_frame(jpeg_buf.tobytes())

            # Yield CPU slice
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[System] Keyboard interrupt received.")
    finally:
        # Shut down web server cleanly
        print("[System] Shutting down local web server...")
        server.shutdown()
        server.server_close()
        
        # Save logs as before
        summary.print_summary()
        logger.save_csv(output_dir=LOG_DIR)
        summary.save_graph(output_dir=LOG_DIR)
        print("[System] Exit completed.")


if __name__ == "__main__":
    main()
