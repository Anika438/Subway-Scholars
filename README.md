# Subway Scholars

Welcome to Subway Scholars, a gamified productivity application that transforms your study schedule into an engaging runner experience.

Take control of your focus time by automatically generating dynamic study sprints using AI, and conquer distractions with an OS-level blocker that forces you to answer academic quizzes if you try to slack off.

---

## Features

- **AI-Powered Missions**: Upload your `.ics` calendar file, course syllabus, or simply type your study goals. The AI integration automatically maps out your available time and generates focused study sprints.
- **Gamified Interface**: An arcade-inspired aesthetic with active mission banners and animated timers.
- **Universal Global Blocker**: When an active mission is running, the Python backend continuously monitors *all* of your active OS windows. If you switch to an application (like YouTube or a video game), the AI evaluates if it is relevant to your sprint. If it determines you are getting distracted for more than 15 seconds, an un-closable overlay pops up on your screen.
- **AI Penalty Quizzes**: To unlock your screen from the blocker, you must correctly answer 3 AI-generated multiple-choice questions tailored to the specific subject you are currently studying.
- **Sprint Management**: You can pause and resume your active sprints (e.g., for a 5, 10, 15, or 20-minute break), during which time the global blocker will safely disengage. Sprints will also automatically end upon completion, displaying a congratulatory message and migrating to your historical "Completed Quests" list.
- **User Profiles**: Create an account to log in and securely track your Total Points, completed sprints, and study history.
- **Emergency Exit**: If you have a legitimate emergency while blocked, you can use the Emergency Exit button in the web app. It requires you to type a randomly generated safety phrase to break your focus streak and unlock the system immediately.

---

## Prerequisites

To run Subway Scholars locally, you'll need:
- Python 3.10+
- A modern web browser
- A free Groq API Key (for the AI generation)

## Getting your API Key
1. Go to console.groq.com
2. Create a free account.
3. Generate a new API Key in the API Keys section.

---

## Installation & Setup

1. **Navigate to the backend directory:**
   ```bash
   cd Subway-Scholars/bouncer
   ```

2. **Install all Python dependencies:**
   ```bash
   pip install fastapi uvicorn pydantic python-multipart pygetwindow icalendar python-dotenv groq bcrypt
   ```

3. **Configure your Environment:**
   Open the `.env` file located in `Subway-Scholars/bouncer/` and paste your Groq API key:
   ```env
   GROQ_API_KEY=your_api_key_here
   ```

---

## How to Run the App

The application runs in two parts: a Python backend and an HTML frontend.

### 1. Start the Backend Guard
Open a terminal, navigate to the `bouncer/` folder, and start the FastAPI server:
```bash
cd bouncer
python main.py
```
Leave this terminal window open. The Python guard is now monitoring for API requests and system distractions.

### 2. Launch the Web App
Open your file explorer, navigate to `Subway-Scholars/app/`, and double-click `auth.html` to register an account or log in. From there, you will be redirected to the main hub.

### 3. Start a Mission
- Type what you want to study into the Mission Board or upload a calendar syllabus.
- Click **Generate Sprints**.
- Click on an active sprint card to begin your focus timer.
- The Global Blocker will now continually assess whatever application you have focused against your active topic.
