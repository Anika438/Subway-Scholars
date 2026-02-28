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

def parse_calendar_for_sprints(ics_file_path: str, target_date: datetime.date = None) -> List[StudySprint]:
    """Parses an .ics file and finds 30+ minute gaps for study sprints."""
    if target_date is None:
        target_date = datetime.date.today()

    try:
        with open(ics_file_path, 'r', encoding='utf-8') as f:
            calendar = icalendar.Calendar.from_ical(f.read())
    except FileNotFoundError:
        print(f"Calendar file not found: {ics_file_path}")
        return []

    # Extract all events for the target date
    events = []
    for component in calendar.walk():
        if component.name == "VEVENT":
            start = component.get('dtstart')
            end = component.get('dtend')
            
            if start and end and hasattr(start.dt, 'date') and start.dt.date() == target_date:
                events.append({
                    "start": start.dt,
                    "end": end.dt,
                    "summary": str(component.get('summary'))
                })

    # Sort events by start time
    events.sort(key=lambda x: x['start'])

    sprints = []
    
    # Define the working day bounds
    day_start = datetime.datetime.combine(target_date, datetime.time(8, 0)).astimezone(events[0]['start'].tzinfo if events else None)
    day_end = datetime.datetime.combine(target_date, datetime.time(22, 0)).astimezone(events[0]['start'].tzinfo if events else None)

    current_time = day_start

    # Find gaps between events
    for event in events:
        gap_duration = (event['start'] - current_time).total_seconds() / 60.0
        
        # If there is a gap of at least 30 minutes, suggest a sprint
        if gap_duration >= 30:
            sprints.append(StudySprint(
                start_time=current_time,
                end_time=event['start'],
                duration_minutes=int(gap_duration),
                suggested_topic="General Study" # Could be enhanced to analyze surrounding events
            ))
            
        current_time = max(current_time, event['end'])

    # Check for a gap after the last event until the end of the day
    if current_time < day_end:
        final_gap = (day_end - current_time).total_seconds() / 60.0
        if final_gap >= 30:
            sprints.append(StudySprint(
                start_time=current_time,
                end_time=day_end,
                duration_minutes=int(final_gap),
                suggested_topic="Evening Review"
            ))

    return sprints


def parse_text_timetable_for_sprints(text: str, target_date: datetime.date = None) -> List[StudySprint]:
    """Generates study sprints from a plain text timetable using Gemini."""
    if target_date is None:
        target_date = datetime.date.today()

    if not client:
        raise Exception("Groq client not initialized. Cannot parse text timetable.")

    prompt = f"""
    You are an AI assistant that finds study gaps in a user's daily schedule.
    Assume the current date and time is {datetime.datetime.now().isoformat()}.
    
    The user will provide text representing either their daily timetable or a general study goal.
    - If they provide a detailed schedule with times, identify open blocks of time that are at least 30 minutes long.
    - If they provide general subjects without explicit times (e.g., 'german and maths quiz'), count the number of distinct subjects. Generate exactly that many 45-minute sprints, one per subject. Use the subject name as the suggested_topic. Do NOT invent extra sprints such as 'Quiz Preparation', 'Review', 'Break', or anything the user did not explicitly name. The number of sprints MUST equal the number of subjects.
    
    Return a JSON array of study sprints matching this exact schema for each object:
    {{"start_time": "YYYY-MM-DDTHH:MM:SS", "end_time": "YYYY-MM-DDTHH:MM:SS", "duration_minutes": "int", "suggested_topic": "string"}}
    The user's schedule/request text:
    "{text}"
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
             # Llama might wrap it like {"sprints": [...]} or just return the list directly, 
             # let's be robust:
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
        error_msg = f"Error parsing text timetable: {repr(e)}"
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
