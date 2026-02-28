import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pygetwindow as gw
import sys
import os

# Add lengths to sys path to import the brain logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'brain')))
try:
    import intelligence
except ImportError:
    print("Warning: Could not import intelligence module from brain folder.")
    intelligence = None

from notification_monitor import NotificationMonitor

import subprocess
import threading
import sys
import time

app = FastAPI(title="The Guard - Focus Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BLACKLIST = ["youtube", "instagram"]

SAFETY_SENTENCES = [
    "I am leaving my focus session for a real emergency.",
    "This is not a distraction I actually need to exit.",
    "I acknowledge that I am breaking my focus streak.",
    "Unlock my system immediately for an important reason."
]

system_state = {
    "unlocked": False,
    "current_challenge": "",
    "is_blocking": False, # Prevent multiple tk windows
    "active_topic": "General Study",
    "monitoring_active": False # Only True after user clicks a sprint
}

# ── Notification Monitor ─────────────────────────────────────────

def _on_notification_held(notif_dict):
    """Callback fired when a notification is held — broadcast via WebSocket."""
    import asyncio as _aio
    try:
        loop = _aio.get_event_loop()
        if loop.is_running():
            _aio.ensure_future(broadcast_event({
                "event": "NOTIFICATION_HELD",
                "notification": notif_dict,
                "held_count": notification_monitor.held_count,
            }))
    except Exception as e:
        print(f"Notification WS broadcast error: {e}", flush=True)

notification_monitor = NotificationMonitor(
    filter_fn=intelligence.filter_notification if intelligence else None,
    on_notification_held=_on_notification_held,
)

class UnlockRequest(BaseModel):
    typed_sentence: str

@app.get("/api/safety/challenge")
async def get_safety_challenge():
    """Generates a random sentence for the Safety Exit feature."""
    system_state["current_challenge"] = random.choice(SAFETY_SENTENCES)
    return {"challenge": system_state["current_challenge"]}

@app.post("/api/safety/unlock")
async def unlock_system(request: UnlockRequest):
    """Validates the typed sentence to unlock the system."""
    if not system_state["current_challenge"]:
        return {"success": False, "message": "Request a challenge first."}
        
    if request.typed_sentence == system_state["current_challenge"]:
        system_state["unlocked"] = True
        system_state["monitoring_active"] = False
        notification_monitor.stop()
        return {"success": True, "message": "System unlocked successfully. You can safely exit."}
    
    return {"success": False, "message": "Typing test failed. Try again."}

@app.post("/api/safety/lock")
async def lock_system(request: dict = None):
    """Relocks the system to resume distraction monitoring."""
    topic = "General Study"
    if request and "topic" in request:
        topic = request["topic"]
        
    system_state["unlocked"] = False
    system_state["current_challenge"] = ""
    system_state["active_topic"] = topic
    system_state["monitoring_active"] = True
    notification_monitor.start(topic)
    print(f"System locked. Monitoring active for topic: {topic}", flush=True)
    return {"success": True, "message": "System locked. Monitoring resumed."}

# --- Brain Integration Endpoints ---

class QuizRequest(BaseModel):
    topic: str
    num_questions: int = 3

@app.post("/api/brain/quiz")
async def get_quiz(request: QuizRequest):
    """Generates a pop-up quiz based on the study topic."""
    if not intelligence:
        return {"error": "Intelligence module not loaded."}
    
    mcqs = intelligence.generate_mcqs(request.topic, request.num_questions)
    return {"quiz": [mcq.dict() for mcq in mcqs]}

@app.post("/api/brain/sprints")
async def get_sprints(
    file: UploadFile = File(None),
    timetable_text: str = Form(None)
):
    """Parses an uploaded calendar file or text timetable and returns recommended study sprints."""
    if not intelligence:
        return {"error": "Intelligence module not loaded."}
        
    if file:
        content = await file.read()
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as f:
            f.write(content)
        try:
            sprints = intelligence.parse_calendar_for_sprints(temp_file_path)
            return {"sprints": [sprint.dict() for sprint in sprints]}
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    elif timetable_text:
        sprints = intelligence.parse_text_timetable_for_sprints(timetable_text)
        return {"sprints": [sprint.dict() for sprint in sprints]}
        
    else:
        raise HTTPException(status_code=400, detail="Please provide either an ICS file or text timetable.")

class NotificationRequest(BaseModel):
    notification_text: str
    current_topic: str

@app.post("/api/brain/filter_notification")
async def filter_notification_endpoint(request: NotificationRequest):
    """Determines if a notification is relevant or should be held."""
    if not intelligence:
        return {"error": "Intelligence module not loaded."}
        
    is_relevant = intelligence.filter_notification(request.notification_text, request.current_topic)
    return {"is_relevant": is_relevant}

# --- Notification Monitor Endpoints ---

@app.get("/api/notifications/held")
async def get_held_notifications():
    """Returns all notifications that were filtered out during the focus session."""
    return {
        "notifications": notification_monitor.get_held(),
        "count": notification_monitor.held_count,
    }

@app.post("/api/notifications/clear")
async def clear_held_notifications():
    """Clears held notifications after the user has reviewed them."""
    count = notification_monitor.clear_held()
    return {"cleared": count}

@app.get("/api/notifications/status")
async def notification_monitor_status():
    """Returns the current state of the notification monitor."""
    return {
        "monitoring": notification_monitor.is_running,
        "held_count": notification_monitor.held_count,
    }

# --- Simulate a notification (for testing the UI) ---

class SimulateNotifRequest(BaseModel):
    app_name: str = "WhatsApp"
    title: str = "New Message"
    body: str = "Hey, wanna hang out tonight?"

@app.post("/api/notifications/simulate")
async def simulate_notification(request: SimulateNotifRequest):
    """
    Fakes a notification for testing. The AI filter decides whether it's
    study-relevant or gets held. Pass study-related text to see it allowed,
    or casual text to see it held.
    """
    from datetime import datetime
    full_text = f"{request.app_name}: {request.title} {request.body}".strip()
    topic = system_state["active_topic"]

    # Run AI filter (or default to blocking if no AI)
    is_relevant = False
    if intelligence:
        try:
            is_relevant = intelligence.filter_notification(full_text, topic)
        except Exception as e:
            print(f"Simulate filter error: {e}", flush=True)

    if is_relevant:
        return {"action": "ALLOWED", "text": full_text, "topic": topic}

    # Treat as held
    from notification_monitor import HeldNotification
    held = HeldNotification(
        app_name=request.app_name,
        title=request.title,
        body=request.body,
        timestamp=datetime.now(),
    )
    notification_monitor.held_notifications.append(held)
    notif_dict = held.to_dict()

    # Broadcast live to connected UI
    await broadcast_event({
        "event": "NOTIFICATION_HELD",
        "notification": notif_dict,
        "held_count": notification_monitor.held_count,
    })

    return {"action": "HELD", "text": full_text, "topic": topic, "held_count": notification_monitor.held_count}

# --- Background Distraction Monitor ---

def launch_os_blocker_sync(topic):
    """Wrapper to run tkinter in main thread context successfully without freezing asyncio."""
    print("Launching OS Focus Blocker UI...", flush=True)
    subprocess.run([sys.executable, "blocker_ui.py", topic])
    print("OS Focus Blocker UI sequence passed. Giving 10s grace period...", flush=True)
    time.sleep(10)
    system_state["is_blocking"] = False

def distraction_monitor_loop():
    """Background thread that continuously scans active windows for blacklisted apps.
    Only runs when monitoring_active is True (after user clicks a sprint card)."""
    print("Distraction Monitor Thread Started.", flush=True)
    while True:
        try:
            if system_state["monitoring_active"] and not system_state["unlocked"] and not system_state["is_blocking"]:
                try:
                    active_window = gw.getActiveWindow()
                except Exception:
                    active_window = None
                if active_window is not None:
                    title = active_window.title.lower()
                    if any(app_name in title for app_name in BLACKLIST):
                        print(f"Distraction detected: '{title}'. Notifying clients!", flush=True)
                        system_state["is_blocking"] = True
                        # Send BLOCK event to all connected UI clients
                        import asyncio as _asyncio
                        try:
                            loop = _asyncio.get_event_loop()
                            if loop.is_running():
                                _asyncio.ensure_future(broadcast_event({
                                    "event": "BLOCK",
                                    "app": title,
                                    "is_blocking": True,
                                    "active_topic": system_state["active_topic"]
                                }))
                        except Exception as e:
                            print(f"WS broadcast error: {e}", flush=True)
                        # Also launch OS blocker as fallback
                        threading.Thread(
                            target=launch_os_blocker_sync,
                            args=(system_state["active_topic"],),
                            daemon=True
                        ).start()
        except Exception as e:
            print(f"Monitor error: {e}", flush=True)
        time.sleep(1)

# Start the monitor thread when the server boots
monitor_thread = threading.Thread(target=distraction_monitor_loop, daemon=True)
monitor_thread.start()

# --- WebSocket (for frontend status updates + BLOCK events) ---

connected_clients: list[WebSocket] = []

async def broadcast_event(event_data: dict):
    """Send an event to all connected WebSocket clients."""
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json(event_data)
        except Exception:
            disconnected.append(client)
    for c in disconnected:
        connected_clients.remove(c)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for frontend status updates and BLOCK events."""
    await websocket.accept()
    connected_clients.append(websocket)
    print(f"Client connected. Total clients: {len(connected_clients)}", flush=True)
    try:
        while True:
            await asyncio.sleep(3)
            await websocket.send_json({
                "event": "STATUS",
                "unlocked": system_state["unlocked"],
                "is_blocking": system_state["is_blocking"],
                "monitoring_active": system_state["monitoring_active"],
                "active_topic": system_state["active_topic"],
                "held_notifications_count": notification_monitor.held_count,
            })
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        print(f"Client disconnected. Total clients: {len(connected_clients)}", flush=True)

# Serve the app/ frontend at /
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))
app.mount("/app", StaticFiles(directory=app_dir, html=True), name="frontend")

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(app_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    # Use to run the app: python main.py
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)

