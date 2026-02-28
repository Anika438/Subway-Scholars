import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    "active_topic": "General Study"
}

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

# --- WebSocket & OS Blocker ---

def launch_os_blocker_sync(topic):
    """Wrapper to run tkinter in main thread context successfully without freezing asyncio."""
    print("Launching OS Focus Blocker UI...")
    subprocess.run([sys.executable, "blocker_ui.py", topic])
    print("OS Focus Blocker UI sequence passed. Giving 10s grace period...")
    time.sleep(10)
    system_state["is_blocking"] = False

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection that pushes BLOCK events when distracting apps are open."""
    await websocket.accept()
    try:
        while True:
            if not system_state["unlocked"] and not system_state["is_blocking"]:
                # Get the currently active window title
                try:
                    active_window = gw.getActiveWindow()
                except Exception:
                    active_window = None
                if active_window is not None:
                    title = active_window.title.lower()
                    # Check against the blacklist
                    if any(app_name in title for app_name in BLACKLIST):
                        # Block!
                        system_state["is_blocking"] = True
                        
                        # Tell frontend
                        await websocket.send_json({
                            "event": "BLOCK", 
                            "app": title,
                            "message": "Distracting application detected!"
                        })
                        
                        # Launch OS overlay in background thread
                        threading.Thread(
                            target=launch_os_blocker_sync, 
                            args=(system_state["active_topic"],), 
                            daemon=True
                        ).start()
                        
            # Check every second
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket.")

if __name__ == "__main__":
    import uvicorn
    # Use to run the app: python main.py
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
