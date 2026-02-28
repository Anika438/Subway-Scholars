# 🚀 Subway Scholars

Welcome to **Subway Scholars**, a gamified productivity application that transforms your study schedule into an engaging, high-stakes runner experience inspired by Subway Surfers!

Take control of your focus time by automatically generating dynamic "Study Sprints" using Meta's Llama 3 AI, and conquer distractions with an unforgiving OS-level blocker that forces you to answer academic quizzes if you try to open social media.

---

## ✨ Features

- **🧠 AI-Powered "Missions"**: Upload your `.ics` calendar file or simply type your study goals (e.g., *"I need to study Calculus and German B1"*). Our Llama 3 integration automatically generates mathematically optimized 45-minute focus sprints.
- **🏃 Gamified Interface**: A vibrant, Subway Surfers-inspired aesthetic complete with glowing buttons, active mission banners, and glowing animated timers.
- **🛡️ The "Guard" OS Blocker**: When an active mission is running, the Python backend continuously monitors your system for distractions (like YouTube or Instagram). If you open them, a 600x600 un-closable overlay pops up!
- **🎓 AI Penalty Quizzes**: To unlock your screen from the Guard, you must correctly answer 3 AI-generated Multiple Choice Questions *specifically tailored to the subject you are currently studying*.
- **🚨 Emergency Exit**: If you have a legitimate emergency, you can use the "Emergency Exit" button in the web app. It requires you to type a randomly generated safety phrase to break your focus streak and unlock the system immediately.

---

## 🛠️ Prerequisites

To run Subway Scholars locally, you'll need:
- **Python 3.10+**
- A **Modern Web Browser** (Chrome, Firefox, Edge, etc.)
- A **Free Groq API Key** (for Llama 3 AI generation).

## 🔑 Getting your API Key
1. Go to [console.groq.com](https://console.groq.com/).
2. Create a free account.
3. Generate a new API Key in the API Keys section.

---

## ⚙️ Installation & Setup

1. **Navigate to the backend directory:**
   ```bash
   cd Subway-Scholars/bouncer
   ```

2. **Install all Python dependencies:**
   ```bash
   pip install fastapi uvicorn pydantic python-multipart pygetwindow icalendar python-dotenv groq
   ```

3. **Configure your Environment:**
   Open the `.env` file located in `Subway-Scholars/bouncer/` and paste your Groq API key:
   ```env
   GROQ_API_KEY=gsk_your_api_key_here
   ```

---

## 🎧 How to Play (Running the App)

The application runs in two parts: a Python backend (The Guard) and an HTML frontend (The User Interface).

### 1. Start the Backend Guard
Open a terminal, navigate to the `bouncer/` folder, and start the FastAPI server:
```bash
cd bouncer
python main.py
```
*Leave this terminal window open! The Guard is now monitoring for API requests and system distractions.*

### 2. Launch the Web App
Open your file explorer, navigate to `Subway-Scholars/app/`, and double-click `index.html` to open it in your browser.

### 3. Start a Mission
- Type what you want to study into the Mission Board (e.g., *"Study History and Physics"*).
- Click **Generate Sprints**.
- Click on an active sprint card to begin your focus timer!

---

## ⚠️ Notes on the OS Blocker
- By default, the blocker looks for window titles containing **"youtube"** or **"instagram"**. You can easily add more restricted apps (like "tiktok" or "discord") to the `BLACKLIST` variable at the top of `bouncer/main.py`.
- The pop-up quiz will pause the OS monitoring for 10 seconds after a successful unlock, giving you enough time to close the distracting window before it catches you again!
