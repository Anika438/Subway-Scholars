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
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

from database import init_db

SECRET_KEY = "my_super_secret_key_for_focusguard"  # In production, use env variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

import database

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        if username is None or user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "id": user_id}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

app = FastAPI(title="The Guard - Focus Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
    "monitoring_active": False, # Only True after user clicks a sprint
    "is_paused": False # True when user clicks pause, stops distraction checks
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
async def lock_system(request: dict = None, current_user: dict = Depends(get_current_user)):
    """Relocks the system to resume distraction monitoring."""
    topic = "General Study"
    if request and "topic" in request:
        topic = request["topic"]
        
    system_state["unlocked"] = False
    system_state["current_challenge"] = ""
    system_state["active_topic"] = topic
    system_state["monitoring_active"] = True
    system_state["is_paused"] = False
    notification_monitor.start(topic)
    print(f"System locked. Monitoring active for topic: {topic}", flush=True)
    return {"success": True, "message": "System locked. Monitoring resumed."}

@app.post("/api/safety/pause")
async def pause_system(current_user: dict = Depends(get_current_user)):
    """Temporarily pauses distraction monitoring."""
    system_state["is_paused"] = True
    print("Session PAUSED. Distraction monitoring halted.", flush=True)
    return {"success": True, "message": "Monitoring paused."}

@app.post("/api/safety/resume")
async def resume_system(current_user: dict = Depends(get_current_user)):
    """Resumes distraction monitoring after a pause."""
    system_state["is_paused"] = False
    print("Session RESUMED. Distraction monitoring active.", flush=True)
    return {"success": True, "message": "Monitoring resumed."}

# --- Auth Endpoints ---

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

@app.post("/api/auth/register")
async def register_user(user: UserCreate):
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (user.username,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = database.hash_password(user.password)
    c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (user.username, hashed_password))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    
    access_token = create_access_token(data={"sub": user.username, "id": user_id})
    return {"access_token": access_token, "token_type": "bearer", "username": user.username}

@app.post("/api/auth/login")
async def login_user(user: UserLogin):
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (user.username,))
    db_user = c.fetchone()
    conn.close()
    
    if not db_user or not database.verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    access_token = create_access_token(data={"sub": db_user["username"], "id": db_user["id"]})
    return {"access_token": access_token, "token_type": "bearer", "username": db_user["username"]}

class SprintSaveRequest(BaseModel):
    topic: str
    duration: int
    score: int

@app.post("/api/sprints/save")
async def save_sprint_endpoint(request: SprintSaveRequest, current_user: dict = Depends(get_current_user)):
    conn = database.get_db_connection()
    c = conn.cursor()
    date_str = datetime.now().isoformat()
    c.execute(
        "INSERT INTO sprints (user_id, topic, duration, score, date) VALUES (?, ?, ?, ?, ?)",
        (current_user["id"], request.topic, request.duration, request.score, date_str)
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": "Sprint saved"}

@app.get("/api/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sprints WHERE user_id = ? ORDER BY id DESC", (current_user["id"],))
    sprints = c.fetchall()
    
    total_score = sum(s["score"] for s in sprints) if sprints else 0
    total_sprints = len(sprints)
    
    sprint_list = [
        {
            "id": s["id"],
            "topic": s["topic"],
            "duration": s["duration"],
            "score": s["score"],
            "date": s["date"]
        } for s in sprints
    ]
    conn.close()
    
    return {
        "username": current_user["username"],
        "total_score": total_score,
        "total_sprints": total_sprints,
        "sprints": sprint_list
    }

# --- Extension Integration Endpoints ---

@app.get("/api/status")
async def get_system_status():
    """Returns basic state for the Chrome extension to display."""
    if system_state["monitoring_active"] and not system_state["unlocked"]:
         return {"active_sprint": {"suggested_topic": system_state["active_topic"]}}
    return {"active_sprint": None}

@app.get("/api/block")
async def trigger_extension_block(url: str = None, topic: str = "General Study"):
    """Triggers the Python tk popup window synchronously when called by the extension."""
    if not system_state["is_blocking"]:
         system_state["is_blocking"] = True
         print(f"Browser distraction detected on {url}. Launching popup...", flush=True)
         threading.Thread(
            target=launch_os_blocker_sync,
            args=(topic,),
            daemon=True
         ).start()
    
    # Return a simple HTML page telling the user they are blocked
    html_content = f"""
    <html>
        <head><title>BLOCKED</title></head>
        <body style="background-color: #111827; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: 'Segoe UI', sans-serif;">
            <h1 style="color: #ff3b3b; font-size: 3rem;">FOCUS PENALTY</h1>
            <p style="font-size: 1.5rem;">You tried to visit a distracting site during your '{topic}' sprint.</p>
            <p>Please complete the challenge on your screen to proceed.</p>
        </body>
    </html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content, status_code=200)

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

@app.get("/api/auth/verify")
async def verify_auth(current_user: dict = Depends(get_current_user)):
    return {"status": "ok", "username": current_user["username"]}

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

class WindowRequest(BaseModel):
    window_title: str
    current_topic: str

@app.post("/api/brain/filter_window")
async def filter_window_endpoint(request: WindowRequest):
    """Determines if a window/tab title is relevant to the topic."""
    if not intelligence:
         return {"is_relevant": False}
    is_relevant = intelligence.is_window_relevant(request.window_title, request.current_topic)
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
    """Background thread that continuously scans active windows.
    Only runs when monitoring_active is True. Uses AI to check relevance
    and aggressively caches results to prevent API spam."""
    print("Distraction Monitor Thread Started.", flush=True)
    pending_distraction_start = None
    last_relevant_title = None

    # Cache format: { "topic_name": { "window_title": is_relevant_bool } }
    relevance_cache = {}

    while True:
        try:
            if system_state["monitoring_active"] and not system_state["unlocked"] and not system_state["is_blocking"] and not system_state["is_paused"]:
                current_topic = system_state["active_topic"]
                if current_topic not in relevance_cache:
                    relevance_cache[current_topic] = {}

                try:
                    active_window = gw.getActiveWindow()
                except Exception:
                    active_window = None

                if active_window is not None:
                    title = active_window.title.strip()
                    if title and title != "Program Manager" and title != "Task Switching":
                        # Fast path: Already confirmed relevant
                        if title == last_relevant_title or relevance_cache[current_topic].get(title) is True:
                            pending_distraction_start = None
                            last_relevant_title = title
                        else:
                            # It's an unknown or confirmed bad window, start/continue grace period
                            if pending_distraction_start is None:
                                pending_distraction_start = time.time()
                                print(f"Unknown app detected: '{title}'. Starting 15s grace period...", flush=True)
                            elif time.time() - pending_distraction_start > 15:
                                print(f"Grace period over. Checking relevance for: '{title}'...", flush=True)
                                
                                # Check if we already know it's a confirmed distraction
                                is_relevant = relevance_cache[current_topic].get(title)

                                if is_relevant is None: # Not in cache, ask AI
                                    print(f"Asking AI about '{title}' for topic '{current_topic}'...", flush=True)
                                    is_relevant = False
                                    if intelligence:
                                        try:
                                            is_relevant = intelligence.is_window_relevant(title, current_topic)
                                        except Exception as e:
                                            print(f"Window relevance check failed: {e}", flush=True)
                                    # Store in cache
                                    relevance_cache[current_topic][title] = is_relevant

                                if not is_relevant:
                                    print(f"Distraction confirmed: '{title}'. Notifying clients!", flush=True)
                                    system_state["is_blocking"] = True
                                    pending_distraction_start = None
                                    
                                    # Send BLOCK event to all connected UI clients
                                    import asyncio as _asyncio
                                    try:
                                        loop = _asyncio.get_event_loop()
                                        if loop.is_running():
                                            _asyncio.ensure_future(broadcast_event({
                                                "event": "BLOCK",
                                                "app": title,
                                                "is_blocking": True,
                                                "active_topic": current_topic
                                            }))
                                    except Exception as e:
                                        print(f"WS broadcast error: {e}", flush=True)
                                    
                                    # Also launch OS blocker as fallback
                                    threading.Thread(
                                        target=launch_os_blocker_sync,
                                        args=(current_topic,),
                                        daemon=True
                                    ).start()
                                else:
                                    print(f"AI deemed '{title}' relevant. Caching and allowing.", flush=True)
                                    last_relevant_title = title
                                    pending_distraction_start = None
                    else:
                        # Empty or basic OS windows don't trigger distractions
                        pending_distraction_start = None
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

