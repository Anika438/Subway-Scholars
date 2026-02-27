"""
Track Shifter — Intelligence Layer Configuration
=================================================
Central configuration for all brain modules.
Defines app classifications, thresholds, timing windows, and quiz parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set
from enum import Enum


# ── App Classification ───────────────────────────────────────────────────────

class AppCategory(Enum):
    """Categories an application can belong to."""
    PRODUCTIVE = "productive"
    DISTRACTION = "distraction"
    NEUTRAL = "neutral"


# Default app classification maps — extendable at runtime
DEFAULT_PRODUCTIVE_APPS: Set[str] = {
    "vscode", "code", "pycharm", "intellij", "sublime_text",
    "notion", "obsidian", "anki", "google_docs", "overleaf",
    "terminal", "cmd", "powershell", "jupyter",
    "excel", "word", "powerpoint", "libreoffice",
    "figma", "blender", "unity",
}

DEFAULT_DISTRACTION_APPS: Set[str] = {
    "instagram", "tiktok", "twitter", "x", "snapchat",
    "youtube", "netflix", "twitch", "reddit",
    "discord", "whatsapp", "telegram", "messenger",
    "candy_crush", "subway_surfers", "among_us",
}


# ── Timing & Session Thresholds ─────────────────────────────────────────────

@dataclass
class SessionConfig:
    """Controls when the Navigator AI schedules study vs. break windows."""
    min_focus_minutes: int = 25          # Pomodoro-style minimum focus block
    max_focus_minutes: int = 90          # Upper bound before forced break
    break_duration_minutes: int = 5      # Short break length
    long_break_minutes: int = 15         # After every N focus blocks
    long_break_interval: int = 4         # Num blocks before long break
    distraction_grace_seconds: int = 10  # Brief app-switch grace period
    daily_goal_minutes: int = 240        # Default daily focus target


# ── Quiz Engine Settings ─────────────────────────────────────────────────────

class QuizDifficulty(Enum):
    """Quiz difficulty tiers — escalate on repeated distractions."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class QuizConfig:
    """Parameters for the Quiz Engine obstacle system."""
    # Gemini API settings
    gemini_api_key: str = "YOUR_GEMINI_API_KEY"   # placeholder — replace at runtime
    gemini_model: str = "gemini-2.0-flash"
    max_retries: int = 3                          # retries on API / parse failure
    default_difficulty: QuizDifficulty = QuizDifficulty.EASY
    escalation_threshold: int = 3        # Distractions before difficulty bump
    num_questions: int = 3               # Questions per quiz obstacle
    time_limit_seconds: int = 30         # Seconds to answer each question
    categories: List[str] = field(default_factory=lambda: [
        "math", "vocabulary", "logic", "science", "general_knowledge",
    ])
    # Penalty: seconds added to cooldown on wrong answer
    wrong_answer_penalty_seconds: int = 15



# ── Notification Filter Settings ─────────────────────────────────────────────

@dataclass
class NotificationConfig:
    """Rules for the Notification Filter AI."""
    # Sentence-transformer model for semantic similarity
    embedding_model: str = "all-MiniLM-L6-v2"
    # Keywords that mark a notification as urgent (always deliver)
    urgent_keywords: List[str] = field(default_factory=lambda: [
        "emergency", "urgent", "deadline", "security", "alert",
        "payment", "overdue", "critical",
    ])
    # Apps whose notifications are always allowed during focus
    whitelisted_senders: Set[str] = field(default_factory=lambda: {
        "calendar", "alarm", "reminder", "bank",
    })
    # Apps whose notifications are always suppressed during focus
    blacklisted_senders: Set[str] = field(default_factory=lambda: {
        "instagram", "tiktok", "snapchat", "twitter",
        "game_center", "promo",
    })
    # Cosine similarity threshold (0-1) — >= threshold → ALLOW, else HOLD
    relevance_threshold: float = 0.35


# ── Analytics Settings ───────────────────────────────────────────────────────

@dataclass
class AnalyticsConfig:
    """Parameters for the end-of-day Analytics Engine."""
    streak_bonus_multiplier: float = 1.25   # XP multiplier per streak day
    base_xp_per_minute: float = 2.0         # XP earned per focused minute
    distraction_xp_penalty: float = 5.0     # XP lost per distraction event
    quiz_correct_xp: float = 10.0           # XP gained per correct quiz
    quiz_wrong_xp_penalty: float = 3.0      # XP lost per wrong quiz answer
    insight_top_n: int = 5                   # Top-N stats in daily summary


# ── Master Config ────────────────────────────────────────────────────────────

@dataclass
class BrainConfig:
    """Top-level configuration container for the entire Intelligence Layer."""
    productive_apps: Set[str] = field(default_factory=lambda: DEFAULT_PRODUCTIVE_APPS.copy())
    distraction_apps: Set[str] = field(default_factory=lambda: DEFAULT_DISTRACTION_APPS.copy())
    session: SessionConfig = field(default_factory=SessionConfig)
    quiz: QuizConfig = field(default_factory=QuizConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)

    def classify_app(self, app_name: str) -> AppCategory:
        """Classify an app by name (case-insensitive)."""
        normalized = app_name.strip().lower().replace(" ", "_")
        if normalized in self.productive_apps:
            return AppCategory.PRODUCTIVE
        if normalized in self.distraction_apps:
            return AppCategory.DISTRACTION
        return AppCategory.NEUTRAL
