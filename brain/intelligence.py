import datetime
import re
from typing import List, Dict, Optional
from pydantic import BaseModel
import icalendar
from groq import Groq
import json
import os
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bouncer', '.env'))
load_dotenv(env_path)

# Initialize Groq Client
try:
    client = Groq() # Automatically looks for GROQ_API_KEY in environment
except Exception as e:
    print(f"Warning: Could not initialize Groq client. Ensure GROQ_API_KEY is set. Error: {e}")
    client = None

class StudySprint(BaseModel):
    start_time: datetime.datetime
    end_time: datetime.datetime
    duration_minutes: int
    suggested_topic: str

class MCQ(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str

def get_sprints_from_ai(text_context: str, target_date: datetime.date) -> List[StudySprint]:
    """Helper function to get study sprints from Groq using a flexible prompt."""
    if not client:
        raise Exception("Groq client not initialized. Cannot parse timetable.")

    prompt = f"""
    You are an AI assistant that plans study sprints for a user.
    Assume the current date and time is {datetime.datetime.now().isoformat()}.
    
    The user will provide text representing their daily schedule/calendar events, a list of study goals, OR a detailed course syllabus/curriculum.
    
    Case A: The user provides a course syllabus, curriculum, or detailed list of topics.
    - Break down the subjects into distinct, chewable topics (e.g., instead of just "Math", use "Math: Integration by Parts").
    - Generate a series of sprints to cover these specific course topics sequentially.
    - The `suggested_topic` MUST be the specific chapter/topic name from the course. This will be used later to generate quizzes, so be precise!
    - The duration of the sprint should be around 45 mins per topic unless otherwise specified.

    Case B: The user provides a list or timeline of busy calendar events.
    - Identify open blocks of free time that are at least 30 minutes long.
    - Create study sprints in those empty gaps. 
    - If the user's calendar events ARE the subjects/course topics they want to study (e.g. "Math: 4pm to 5pm"), then make the `suggested_topic` exactly that. 
    - Otherwise, if the events are just "busy" indicators (e.g. "Lunch"), name the `suggested_topic` something relevant to the time of day (e.g., 'Morning Study Session').
    - The duration of the sprint should fill the available gap in the calendar.

    Case C: The user provides a list of general subjects to study without explicit free/busy times.
    - Count the number of distinct subjects provided. 
    - Generate EXACTLY that many sprints, one per subject.
    - The `suggested_topic` MUST be the name of the subject. 
    - Do NOT invent extra sprints (e.g., 'Quiz Preparation', 'Review', 'Break'). The number of sprints MUST equal the number of subjects.
    
    Return a JSON object with a "sprints" key containing an array of study sprints matching this exact schema:
    {{
        "sprints": [
            {{
                "start_time": "YYYY-MM-DDTHH:MM:SS",
                "end_time": "YYYY-MM-DDTHH:MM:SS", 
                "duration_minutes": int, 
                "suggested_topic": "Specific Topic Name",
                "session_type": "Sprint" | "Marathon"
            }}
        ]
    }}
    
    The user's input text:
    "{text_context}"
    """

    try:
        # Use Groq JSON mode to enforce the StudySprint format
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        # Parse the structured JSON response
        raw_json = response.choices[0].message.content
        sprints_dict = json.loads(raw_json)
        
        # Unpack dicts into Pydantic models (handling the array wrapping if any)
        sprints_data = []
        if isinstance(sprints_dict, dict):
             for key in sprints_dict:
                 if isinstance(sprints_dict[key], list):
                     for item in sprints_dict[key]:
                         sprints_data.append(StudySprint(**item))
                     break
        elif isinstance(sprints_dict, list):
             for item in sprints_dict:
                 sprints_data.append(StudySprint(**item))
                 
        print("Sprints Data from Groq:", sprints_data, flush=True)
        if sprints_data:
            return sprints_data
            
    except Exception as e:
        error_msg = f"Error parsing timetable: {repr(e)}"
        print(error_msg, flush=True)
        # Create a fallback sprint when rate limited
        return [
            StudySprint(
                start_time=datetime.datetime.now(),
                end_time=datetime.datetime.now() + datetime.timedelta(minutes=45),
                duration_minutes=45,
                suggested_topic="Fallback Study (API Offline)"
            )
        ]
        
    return []


def parse_calendar_for_sprints(ics_file_path: str, target_date: datetime.date = None) -> List[StudySprint]:
    """Parses an .ics file and uses AI to find study gaps."""
    if target_date is None:
        target_date = datetime.date.today()

    try:
        with open(ics_file_path, 'r', encoding='utf-8') as f:
            calendar = icalendar.Calendar.from_ical(f.read())
    except FileNotFoundError:
        print(f"Calendar file not found: {ics_file_path}")
        return []

    events_text = ["Here are the calendar events for the day:"]
    for component in calendar.walk():
        if component.name == "VEVENT":
            start = component.get('dtstart')
            end = component.get('dtend')
            
            if start and end and hasattr(start.dt, 'date') and start.dt.date() == target_date:
                events_text.append(f"- {component.get('summary')} from {start.dt} to {end.dt}")

    if len(events_text) == 1:
        events_text.append("No events scheduled for today. The whole day is free.")

    return get_sprints_from_ai("\n".join(events_text), target_date)


def parse_text_timetable_for_sprints(text: str, target_date: datetime.date = None) -> List[StudySprint]:
    """Generates study sprints from a plain text timetable using AI."""
    if target_date is None:
        target_date = datetime.date.today()
        
    return get_sprints_from_ai(text, target_date)


def generate_mcqs(topic: str, num_questions: int = 3) -> List[MCQ]:
    """Generates MCQs using Gemini based on the study topic."""
    
    dummy_questions = [
        MCQ(
            question=f"Dummy Question about {topic}?",
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation="This is a fallback explanation because the API client failed."
        ) for _ in range(num_questions)
    ]
    
    if not client:
        print("Groq client not initialized. Returning dummy MCQs.")
        return dummy_questions

    prompt = f"""
    You are an expert tutor. Generate {num_questions} multiple-choice questions (MCQs) 
    about the following topic: '{topic}'.
    
    Ensure the questions are challenging but fair.
    Provide 4 options for each question.
    
    Return a JSON dictionary containing a "questions" key with an array matching this schema:
    {{"question": "string", "options": ["string", "string", "string", "string"], "correct_answer": "string", "explanation": "string"}}
    """

    try:
         # Use Groq JSON mode
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        # Parse the structured JSON response
        raw_json = response.choices[0].message.content
        mcqs_dict = json.loads(raw_json)
        
        mcqs_data = []
        if "questions" in mcqs_dict:
             for item in mcqs_dict["questions"]:
                 mcqs_data.append(MCQ(**item))
                 
        if mcqs_data:
            return mcqs_data
            
    except Exception as e:
        print(f"Error generating MCQs, falling back to dummies: {e}")
        
    return dummy_questions


def filter_notification(notification_text: str, current_study_topic: str) -> bool:
    """
    Uses Gemini to determine if a notification is relevant to the study topic.
    Returns True if relevant (allow through), False if irrelevant (hold for recap).
    """
    if not client:
        return False # Default to blocking if no AI available to judge

    prompt = f"""
    The user is currently studying: '{current_study_topic}'.
    They just received the following notification:
    "{notification_text}"

    Is this notification directly relevant to their study topic, or is it an urgent emergency that they must see immediately? 
    Answer MUST be exactly 'YES' (if relevant/urgent) or 'NO' (if distracting/can wait).
    """
    
    try:
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        
        answer = response.choices[0].message.content.strip().upper()
        return answer.startswith("YES")
        
    except Exception as e:
         print(f"Error filtering notification: {e}")
         return False

# Example Usage
if __name__ == "__main__":
    print("--- Brain Module Test ---")
    
    # Example 1: Generate MCQs (requires GROQ_API_KEY)
    print("\nGenerating MCQs for 'Photosynthesis'...")
    qs = generate_mcqs("Photosynthesis")
    for q in qs:
        print(f"Q: {q.question}")
        print(f"A: {q.correct_answer} - {q.explanation}\n")
        
    # Example 2: Filter Notification
    print("Filtering Notification...")
    is_relevant = filter_notification("Hey, do you want to play games tonight?", "Deep Learning Math")
    print(f"Notification allowed? {is_relevant}")
    
    is_relevant2 = filter_notification("Here is the Deep Learning cheat sheet you asked for.", "Deep Learning Math")
    print(f"Notification allowed? {is_relevant2}")
