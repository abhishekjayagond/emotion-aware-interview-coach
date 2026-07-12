"""
web_server.py
-------------
A zero-dependency multi-threaded HTTP server.
Serves static frontend files and exposes APIs for:
  - MJPEG video streaming (/api/video)
  - Real-time Server-Sent Events (/api/events)
  - Action controllers (/api/action/<cmd>)
  - Final summary reporting (/api/report)
"""

from __future__ import annotations

import os
import mimetypes
import json
import time
import queue
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional, Any

# Global server state
_state_lock = threading.Lock()
latest_jpeg: bytes = b""
session_state: dict[str, Any] = {}
action_queue: queue.Queue[str] = queue.Queue()
report_data: dict[str, Any] = {}

# Active SSE client queues
sse_clients: list[queue.Queue[str]] = []
clients_lock = threading.Lock()

def _make_serializable(obj: Any) -> Any:
    """Recursively converts numpy types and other objects into JSON serializable standard types."""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_serializable(x) for x in obj]
    elif hasattr(obj, "item"):  # Handles numpy scalars like np.float32, np.int64
        try:
            return obj.item()
        except Exception:
            return obj
    elif isinstance(obj, (float, int, str, bool)) or obj is None:
        return obj
    try:
        if hasattr(obj, '__float__'): return float(obj)
        if hasattr(obj, '__int__'): return int(obj)
    except Exception:
        pass
    return obj


def update_state(state: dict[str, Any]) -> None:
    """Updates the global session state and notifies all SSE clients."""
    global session_state
    with _state_lock:
        session_state = _make_serializable(state)
        data_str = json.dumps(session_state)
    
    # Broadcast to SSE clients
    with clients_lock:
        for q in sse_clients:
            try:
                q.put_nowait(data_str)
            except queue.Full:
                pass

def set_latest_frame(jpeg_bytes: bytes) -> None:
    """Sets the latest JPEG compressed frame bytes for streaming."""
    global latest_jpeg
    with _state_lock:
        latest_jpeg = jpeg_bytes

def set_report_data(report: dict[str, Any]) -> None:
    """Sets the final summary report data."""
    global report_data
    with _state_lock:
        report_data = _make_serializable(report)

def get_next_action() -> Optional[str]:
    """Retrieves the next pending action from the queue, if any."""
    try:
        return action_queue.get_nowait()
    except queue.Empty:
        return None


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server to handle video streaming and SSE requests in parallel."""
    allow_reuse_address = True
    daemon_threads = True


class InterviewHTTPHandler(BaseHTTPRequestHandler):
    """Request handler supporting Web UI files, MJPEG streaming, SSE, and control APIs."""
    
    # Disable logging each request to console to avoid cluttering terminal
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        path = self.path
        
        # 1. API: Video Stream
        if path == "/api/video":
            self.handle_video_stream()
            return
            
        # 2. API: Server-Sent Events
        elif path == "/api/events":
            self.handle_sse()
            return
            
        # 3. API: Action handlers
        elif path.startswith("/api/action/"):
            action = path.split("/api/action/")[-1]
            action_queue.put(action)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "action_queued": action}).encode())
            return
            
        # 4. API: Report Summary Data
        elif path == "/api/report":
            with _state_lock:
                data = json.dumps(report_data)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data.encode())
            return
            
        # 5. Serve static web files
        else:
            self.serve_static_file()

    def handle_video_stream(self) -> None:
        """Streams webcam frames as an MJPEG multipart response."""
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        last_sent_time = 0.0
        try:
            while True:
                # Limit frame streaming rate in browser to ~30 fps
                now = time.time()
                elapsed = now - last_sent_time
                if elapsed < 0.033:
                    time.sleep(0.033 - elapsed)
                
                with _state_lock:
                    frame_bytes = latest_jpeg
                
                if frame_bytes:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame_bytes)}\r\n\r\n".encode())
                    self.wfile.write(frame_bytes)
                    self.wfile.write(b"\r\n")
                    last_sent_time = time.time()
                else:
                    time.sleep(0.01)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            # Client disconnected
            pass

    def handle_sse(self) -> None:
        """Feeds realtime interview data updates via Server-Sent Events."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # Send initial state immediately
        with _state_lock:
            init_data = json.dumps(session_state)
        self.wfile.write(f"data: {init_data}\n\n".encode())
        self.wfile.flush()

        # Register a local queue for state broadcasts
        q: queue.Queue[str] = queue.Queue(maxsize=20)
        with clients_lock:
            sse_clients.append(q)
            
        try:
            while True:
                # Wait for state changes with a timeout (keepalive)
                try:
                    data = q.get(timeout=2.0)
                    self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.flush()
                except queue.Empty:
                    # Ping client to keep connection alive
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass
        finally:
            with clients_lock:
                if q in sse_clients:
                    sse_clients.remove(q)

    def serve_static_file(self) -> None:
        """Helper to resolve paths and serve files from the web folder."""
        # Sanitize path: strip query parameters
        clean_path = self.path.split("?")[0]
        if clean_path == "/":
            clean_path = "/index.html"
            
        # Build path to file in project's "web" directory
        root = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(root, "web", clean_path.lstrip("/"))
        
        # Check security and existence
        if not os.path.abspath(file_path).startswith(os.path.join(root, "web")):
            self.send_error(403, "Forbidden")
            return
            
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            self.send_error(404, "File Not Found")
            return
            
        # Get mime type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"
            
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self.send_error(500, "Internal Server Error")


def start_server(port: int = 8000) -> HTTPServer:
    """Starts the threaded HTTP server on a separate daemon thread."""
    server = ThreadedHTTPServer(("localhost", port), InterviewHTTPHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[WebUI] Server running locally at http://localhost:{port}")
    return server
