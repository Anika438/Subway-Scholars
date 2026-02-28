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
        window_width = 700
        window_height = 600
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
        self.title_font = ("Consolas", 32, "bold")
        self.body_font = ("Arial", 16)
        self.btn_font = ("Arial", 14, "bold")
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
        
        title_lbl = tk.Label(self.root, text="DISTRACTION DETECTED!", font=self.title_font, fg=self.color_danger, bg=self.color_bg)
        title_lbl.pack(pady=(100, 20))
        
        info_lbl = tk.Label(self.root, text=f"You must answer 3 questions about '{self.topic}' to unlock.", font=self.body_font, fg="#fff", bg=self.color_bg)
        info_lbl.pack()
        
        # Failsafe button just in case AI hangs
        self.failsafe_btn = tk.Button(self.root, text="Exit (AI Failed)", bg="#555", fg="#fff", command=self.unlock_system)
        self.failsafe_btn.pack(pady=20)

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

        # Top Banner
        header = tk.Frame(self.root, bg="#000", height=100)
        header.pack(fill="x", side="top")
        
        title_lbl = tk.Label(header, text="FOCUS PENALTY", font=("Helvetica", 24, "bold"), fg=self.color_danger, bg="#000")
        title_lbl.pack(pady=30)
        
        progress_lbl = tk.Label(self.root, text=f"Question {self.current_q_index + 1} of {self.correct_answers_needed}", font=("Arial", 12, "bold"), fg=self.color_primary, bg=self.color_bg)
        progress_lbl.pack(pady=20)

        # Question Text
        q_text = tk.Label(self.root, text=current_mcq.question, font=("Arial", 16), fg="#fff", bg=self.color_bg, wraplength=600, justify="center")
        q_text.pack(pady=20)

        # Container for evenly spaced buttons
        btn_frame = tk.Frame(self.root, bg=self.color_bg)
        btn_frame.pack(pady=20)

        # Create buttons
        for opt in current_mcq.options:
            btn = tk.Button(
                btn_frame, 
                text=opt, 
                font=("Arial", 11, "bold"), 
                bg="#333", 
                fg="#fff",
                activebackground=self.color_primary,
                activeforeground="#000",
                width=50,
                height=2,
                bd=0,
                cursor="hand2",
                command=lambda o=opt: self.check_answer(o, current_mcq)
            )
            btn.pack(pady=5)
            
        self.feedback_lbl = tk.Label(self.root, text="", font=self.btn_font, bg=self.color_bg)
        self.feedback_lbl.pack(pady=10)
        
        # Failsafe button
        failsafe_btn2 = tk.Button(self.root, text="Failsafe Exit/Skip", bg="#555", fg="#fff", command=self.unlock_system)
        failsafe_btn2.pack(pady=10)

    def check_answer(self, selected: str, mcq):
        """Validates click and moves to next or penalizes."""
        if selected == mcq.correct_answer:
            self.current_q_index += 1
            if self.current_q_index >= self.correct_answers_needed:
                self.feedback_lbl.config(text="Challenge Passed. Unlocking...", fg="#00E676")
                self.root.after(1000, self.unlock_system)
            else:
                self.build_ui_question()
        else:
            self.feedback_lbl.config(text=f"WRONG! {mcq.explanation}", fg=self.color_danger, wraplength=800)

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
