import tkinter as tk
from tkinter import messagebox
import sys
import os
import threading

# Import our AI module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'brain')))
import intelligence

class SubwayBlockerUI:
    def __init__(self, topic: str):
        self.topic = topic
        self.mcqs = []
        self.current_q_index = 0
        self.correct_answers_needed = 3
        
        # Setup centered floating window
        self.root = tk.Tk()
        self.root.title("Focus Blocker")
        
        # Make it 700x600 and center it
        window_width = 750
        window_height = 650
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width / 2)
        center_y = int(screen_height/2 - window_height / 2)
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        self.root.attributes("-topmost", True)    # Always on top
        self.root.configure(bg="#111827")
        
        # Prevent ALT+F4
        self.root.protocol("WM_DELETE_WINDOW", self.disable_event)
        
        # Fonts & Colors
        self.title_font = ("Impact", 34, "normal")
        self.body_font = ("Segoe UI", 16)
        self.btn_font = ("Segoe UI", 14, "bold")
        self.color_danger = "#ff3b3b"
        self.color_primary = "#FF9800"
        self.color_bg = "#111827"
        
        self.build_ui_loading()
        
        # Fetch MCQs in background so UI doesn't freeze
        threading.Thread(target=self.fetch_questions, daemon=True).start()

    def disable_event(self):
        """Prevents closing the window normally."""
        pass

    def build_ui_loading(self):
        """Displays a loading screen while Gemini generates the 3 questions."""
        self.clear_ui()
        
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        colors = ["#171e2e", "#131926"]
        for i in range(30):
            y = i * 30
            self.canvas.create_rectangle(0, y, 1000, y+30, fill=colors[i%2], outline="")
            
        self.canvas.create_text(375, 150, text="DISTRACTION DETECTED!", font=self.title_font, fill=self.color_danger)
        
        txt = f"You must answer 3 questions about '{self.topic}' to unlock."
        self.canvas.create_text(375, 250, text=txt, font=self.body_font, fill="#fff", width=600, justify="center")
        
        self.canvas.create_text(375, 350, text="Loading questions...", font=("Segoe UI", 14), fill=self.color_primary)

    def fetch_questions(self):
        """Runs concurrently to fetch questions from Gemini."""
        time_limit = 10 # 10 seconds timeout
        def generator():
            try:
                self.mcqs = intelligence.generate_mcqs(self.topic, self.correct_answers_needed)
            except Exception as e:
                print("Error generating quiz:", e)
                
        thread = threading.Thread(target=generator, daemon=True)
        thread.start()
        thread.join(timeout=time_limit)
        
        if thread.is_alive() or not getattr(self, "mcqs", None):
            print("Gemini API timed out or failed. Freeing user.")
            self.root.after(0, self.unlock_system)
        else:
            self.root.after(0, self.build_ui_question)

    def clear_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def build_ui_question(self):
        """Renders the current question onto the fullscreen overlay."""
        self.clear_ui()
        
        if self.current_q_index >= len(self.mcqs):
            self.unlock_system()
            return
            
        current_mcq = self.mcqs[self.current_q_index]

        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        colors = ["#171e2e", "#131926"]
        for i in range(30):
            y = i * 30
            self.canvas.create_rectangle(0, y, 1000, y+30, fill=colors[i%2], outline="")
            
        # Top banner background
        self.canvas.create_rectangle(0, 0, 1000, 80, fill="#0f172a", outline="")
        self.canvas.create_text(375, 40, text="FOCUS PENALTY", font=("Impact", 28, "normal"), fill=self.color_primary)
        
        # Details & text
        self.canvas.create_text(375, 120, text=f"Question {self.current_q_index + 1} of {self.correct_answers_needed}", font=("Segoe UI", 12, "bold"), fill=self.color_primary)
        self.canvas.create_text(375, 180, text=current_mcq.question, font=("Segoe UI", 16), fill="#fff", width=650, justify="center")

        # Buttons placed evenly
        start_y = 280
        for i, opt in enumerate(current_mcq.options):
            btn = tk.Button(
                self.root, 
                text=opt, 
                font=("Segoe UI", 12, "bold"), 
                bg="#334155", 
                fg="#f8fafc",
                activebackground=self.color_primary,
                activeforeground="#000",
                width=50,
                height=2,
                bd=0,
                cursor="hand2",
                command=lambda o=opt: self.check_answer(o, current_mcq)
            )
            self.canvas.create_window(375, start_y + (i * 65), window=btn)
            
        self.feedback_text = self.canvas.create_text(375, 570, text="", font=self.btn_font, fill=self.color_danger, width=650, justify="center")
        


    def check_answer(self, selected: str, mcq):
        """Validates click and moves to next or penalizes."""
        if selected == mcq.correct_answer:
            self.current_q_index += 1
            if self.current_q_index >= self.correct_answers_needed:
                self.canvas.itemconfig(self.feedback_text, text="Challenge Passed. Unlocking...", fill="#00E676")
                self.root.after(1000, self.unlock_system)
            else:
                self.build_ui_question()
        else:
            self.canvas.itemconfig(self.feedback_text, text=f"WRONG! {mcq.explanation}", fill=self.color_danger)

    def unlock_system(self):
        """Destroys the tkinter blocking window entirely."""
        self.root.destroy()
        
def block_screen(topic="General Study"):
    """Entry point to trigger the tkinter blocker synchronously. Should be run in a separate thread depending on the server loop."""
    ui = SubwayBlockerUI(topic)
    ui.root.mainloop()

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "General Study"
    block_screen(topic)
