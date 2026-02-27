"""
Track Shifter -- Analytics Engine
==================================
Generates end-of-day summary insights using rule-based logic.

Input:
    total_focus_time_minutes   – minutes spent in focus mode
    distraction_attempts       – number of times user switched to distractions
    quiz_accuracy_percentage   – quiz accuracy as 0-100
    peak_focus_hour            – the hour (0-23) when user was most focused

Output:
    {
        "focus_score":              int 0-100,
        "consistency_rating":       "Low" | "Medium" | "High",
        "suggested_next_day_sprint": int (minutes),
        "burnout_risk":             "Low" | "Medium" | "High"
    }
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from config import BrainConfig


# -- Rule constants -----------------------------------------------------------

# Focus score weights (must sum to 100)
_W_FOCUS_TIME = 40       # weight for total focus minutes
_W_DISTRACTION = 30      # weight for distraction penalty
_W_QUIZ = 30             # weight for quiz accuracy

# Focus-time benchmarks (minutes)
_EXCELLENT_FOCUS = 240   # 4 h  → full marks
_GOOD_FOCUS = 120        # 2 h  → ~75 %

# Distraction thresholds
_DIST_LOW = 3            # <= 3  → minimal penalty
_DIST_HIGH = 10          # >= 10 → maximum penalty

# Consistency thresholds (applied to focus_score)
_CONSISTENCY_HIGH = 70
_CONSISTENCY_MED = 40

# Burnout thresholds
_BURNOUT_FOCUS_HIGH = 300   # > 5 h focus → risk rises
_BURNOUT_FOCUS_EXTREME = 420  # > 7 h → high risk
_BURNOUT_DIST_HIGH = 8      # many distractions amplify risk

# Sprint suggestion bounds
_SPRINT_MIN = 15         # never suggest less than 15 min
_SPRINT_MAX = 50         # never suggest more than 50 min
_SPRINT_DEFAULT = 25     # Pomodoro standard


# -- Scoring helpers ----------------------------------------------------------

def _focus_time_score(minutes: float) -> float:
    """0-100 sub-score based on total focus time."""
    if minutes <= 0:
        return 0.0
    if minutes >= _EXCELLENT_FOCUS:
        return 100.0
    # Linear ramp to 75 at GOOD, then slower ramp to 100
    if minutes <= _GOOD_FOCUS:
        return (minutes / _GOOD_FOCUS) * 75.0
    # GOOD → EXCELLENT  (75 → 100)
    extra = (minutes - _GOOD_FOCUS) / (_EXCELLENT_FOCUS - _GOOD_FOCUS)
    return 75.0 + extra * 25.0


def _distraction_score(attempts: int) -> float:
    """0-100 sub-score (100 = perfect, 0 = heavily distracted)."""
    if attempts <= 0:
        return 100.0
    if attempts >= _DIST_HIGH:
        return 0.0
    if attempts <= _DIST_LOW:
        # Gentle penalty: 100 → 70
        return 100.0 - (attempts / _DIST_LOW) * 30.0
    # _DIST_LOW → _DIST_HIGH  (70 → 0)
    ratio = (attempts - _DIST_LOW) / (_DIST_HIGH - _DIST_LOW)
    return 70.0 * (1 - ratio)


def _quiz_score(accuracy_pct: float) -> float:
    """0-100 sub-score — simply the accuracy itself."""
    return max(0.0, min(100.0, accuracy_pct))


# -- Core engine --------------------------------------------------------------

class AnalyticsEngine:
    """
    Rule-based end-of-day analytics engine.

    Usage::

        engine = AnalyticsEngine()
        report = engine.generate_report(
            total_focus_time_minutes=135,
            distraction_attempts=4,
            quiz_accuracy_percentage=80,
            peak_focus_hour=10,
        )
        print(report)
    """

    def __init__(self, config: Optional[BrainConfig] = None) -> None:
        self.config = config or BrainConfig()
        self._history: list[Dict[str, Any]] = []

    # -- Public API -----------------------------------------------------------

    @property
    def history(self) -> list[Dict[str, Any]]:
        return list(self._history)

    def generate_report(
        self,
        total_focus_time_minutes: float,
        distraction_attempts: int,
        quiz_accuracy_percentage: float,
        peak_focus_hour: int,
    ) -> Dict[str, Any]:
        """
        Produce the end-of-day summary.

        Args:
            total_focus_time_minutes:  minutes in focus mode today
            distraction_attempts:      count of distraction switches
            quiz_accuracy_percentage:  quiz accuracy 0-100
            peak_focus_hour:           hour (0-23) of best focus

        Returns:
            {
                "focus_score": int 0-100,
                "consistency_rating": "Low" | "Medium" | "High",
                "suggested_next_day_sprint": int (minutes),
                "burnout_risk": "Low" | "Medium" | "High"
            }
        """
        focus_score = self._compute_focus_score(
            total_focus_time_minutes,
            distraction_attempts,
            quiz_accuracy_percentage,
        )
        consistency = self._compute_consistency(focus_score)
        sprint = self._compute_sprint_suggestion(
            total_focus_time_minutes,
            distraction_attempts,
            focus_score,
        )
        burnout = self._compute_burnout_risk(
            total_focus_time_minutes,
            distraction_attempts,
            peak_focus_hour,
        )

        report: Dict[str, Any] = {
            "focus_score": focus_score,
            "consistency_rating": consistency,
            "suggested_next_day_sprint": sprint,
            "burnout_risk": burnout,
        }

        self._history.append(report)
        return report

    # -- Internal rules -------------------------------------------------------

    @staticmethod
    def _compute_focus_score(
        minutes: float,
        distractions: int,
        quiz_pct: float,
    ) -> int:
        """Weighted composite score (0-100)."""
        ft = _focus_time_score(minutes)
        ds = _distraction_score(distractions)
        qs = _quiz_score(quiz_pct)

        raw = (ft * _W_FOCUS_TIME + ds * _W_DISTRACTION + qs * _W_QUIZ) / 100
        return int(round(max(0, min(100, raw))))

    @staticmethod
    def _compute_consistency(focus_score: int) -> str:
        """
        Consistency rating derived from focus score.

        High   → score >= 70
        Medium → score 40-69
        Low    → score < 40
        """
        if focus_score >= _CONSISTENCY_HIGH:
            return "High"
        if focus_score >= _CONSISTENCY_MED:
            return "Medium"
        return "Low"

    @staticmethod
    def _compute_sprint_suggestion(
        minutes: float,
        distractions: int,
        focus_score: int,
    ) -> int:
        """
        Suggest tomorrow's sprint duration (minutes).

        Rules:
        - High score + low distractions  → increase sprint (up to 50 min)
        - Low score  + high distractions → shorten sprint (down to 15 min)
        - Otherwise                      → stay at default 25 min
        """
        sprint = _SPRINT_DEFAULT

        # Reward strong days
        if focus_score >= 75 and distractions <= _DIST_LOW:
            # Scale up: +1 min per 5 score points above 75
            sprint += (focus_score - 75) // 5

        # Ease off after struggling days
        if focus_score < 40:
            sprint -= 5
        if distractions >= _DIST_HIGH:
            sprint -= 5

        # Over-focus adjustment: if user already did a huge day, suggest shorter
        if minutes >= _BURNOUT_FOCUS_HIGH:
            sprint -= 5

        return max(_SPRINT_MIN, min(_SPRINT_MAX, sprint))

    @staticmethod
    def _compute_burnout_risk(
        minutes: float,
        distractions: int,
        peak_hour: int,
    ) -> str:
        """
        Burnout risk assessment.

        Factors:
        - Very long focus time (> 5 h)        → increases risk
        - Extreme focus time (> 7 h)          → high risk
        - High distractions during long focus  → amplifies risk
        - Late-night peak focus (22-4)         → increases risk
        """
        risk_points = 0

        # Focus duration load
        if minutes >= _BURNOUT_FOCUS_EXTREME:
            risk_points += 3
        elif minutes >= _BURNOUT_FOCUS_HIGH:
            risk_points += 2

        # High distraction + long focus = frustration signal
        if minutes >= _GOOD_FOCUS and distractions >= _BURNOUT_DIST_HIGH:
            risk_points += 2

        # Late-night studying
        if peak_hour >= 22 or peak_hour <= 4:
            risk_points += 1

        if risk_points >= 4:
            return "High"
        if risk_points >= 2:
            return "Medium"
        return "Low"
