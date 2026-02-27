"""
Track Shifter — Intelligence Layer Entry Point
================================================
Wires together all four brain modules and runs a demonstration simulation.

Modules:
  • Navigator      — session state machine & scheduling
  • QuizEngine     — quiz obstacle generation & grading
  • NotificationFilter — notification relevance scoring
  • AnalyticsEngine    — XP, streaks, and daily insights

Run:
    python main.py
"""

from __future__ import annotations

import time

from config import BrainConfig
from navigator import Navigator, NavigatorDecision
from quiz_engine import QuizEngine
from notification_filter import NotificationFilter, Notification
from analytics import AnalyticsEngine, FocusRecord, QuizRecord


# ── Helpers ──────────────────────────────────────────────────────────────────

def _header(title: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def _sub(text: str) -> None:
    print(f"  → {text}")


# ── Demo Simulation ─────────────────────────────────────────────────────────

def run_demo() -> None:
    """Full demonstration of the Track Shifter Intelligence Layer."""

    config = BrainConfig()

    # Instantiate all modules
    navigator = Navigator(config)
    quiz_engine = QuizEngine(config)
    notif_filter = NotificationFilter(config)
    analytics = AnalyticsEngine(config)

    # ── 1. Navigator — Start Session ─────────────────────────────────────
    _header("1 · NAVIGATOR — Starting Focus Session")
    event = navigator.start_session()
    _sub(f"State: {navigator.state.value}")
    _sub(f"Decision: {event.decision.value} — {event.reason}")

    # Simulate productive app usage
    _header("2 · NAVIGATOR — App Switch: VS Code (productive)")
    event = navigator.on_app_switch("vscode")
    _sub(f"Decision: {event.decision.value} — {event.reason}")

    # Simulate distraction
    _header("3 · NAVIGATOR — App Switch: Instagram (distraction)")
    # Force past grace period
    navigator._last_switch_time = time.time() - 20
    event = navigator.on_app_switch("instagram")
    _sub(f"Decision: {event.decision.value} — {event.reason}")
    _sub(f"Distraction count: {navigator.distraction_count}")

    # ── 2. Quiz Engine — Generate & Grade ────────────────────────────────
    _header("4 · QUIZ ENGINE — Generating Quiz Obstacle")
    session = quiz_engine.generate_quiz(distraction_count=navigator.distraction_count)
    question = session.questions[0]
    _sub(f"Session: {session.session_id}")
    _sub(f"Difficulty: {question.difficulty.value}")
    _sub(f"Question: {question.question_text}")
    for i, choice in enumerate(question.choices):
        marker = "✓" if i == question.correct_index else " "
        _sub(f"  [{marker}] {i}. {choice}")

    # Simulate correct answer
    result = quiz_engine.grade_answer(question, user_choice=question.correct_index, elapsed_seconds=8.0)
    session.results.append(result)
    _sub(f"Correct: {result.is_correct} | Time: {result.time_taken_seconds}s")

    # Tell navigator quiz is done
    nav_event = navigator.on_quiz_completed(passed=session.passed)
    _sub(f"Navigator: {nav_event.decision.value} — {nav_event.reason}")

    # ── 3. Notification Filter ───────────────────────────────────────────
    _header("5 · NOTIFICATION FILTER — Evaluating Notifications")

    notifications = [
        Notification("n1", "calendar", "Meeting in 10 min", "Standup at 3 PM"),
        Notification("n2", "instagram", "New follower", "john_doe started following you"),
        Notification("n3", "bank", "Payment alert", "Urgent: payment of $250 due"),
        Notification("n4", "promo", "50% off!", "Limited time sale on shoes"),
    ]

    for notif in notifications:
        res = notif_filter.evaluate(notif, is_focus=True)
        _sub(f"[{res.verdict.value:>8}] {notif.sender:>12}: \"{notif.title}\" "
             f"(score={res.relevance_score:.2f}) — {res.reason}")

    _sub(f"Queued for later: {len(notif_filter.queue)} notification(s)")

    # ── 4. Analytics Engine ──────────────────────────────────────────────
    _header("6 · ANALYTICS — Daily Report")

    now = time.time()
    analytics.log_focus(FocusRecord(
        start_time=now - 3600, end_time=now - 1800,
        app_name="vscode", distraction_events=1,
    ))
    analytics.log_focus(FocusRecord(
        start_time=now - 1500, end_time=now,
        app_name="notion", distraction_events=0,
    ))
    analytics.log_quiz(QuizRecord(
        quiz_id=session.session_id,
        correct=1, total=1,
    ))

    analytics.update_streak(goal_met_today=True)
    report = analytics.generate_report()

    _sub(f"Date: {report.date}")
    _sub(f"Focus: {report.total_focus_minutes} min")
    _sub(f"Distractions: {report.total_distractions}")
    _sub(f"Quiz accuracy: {report.quiz_accuracy:.0%}")
    _sub(f"XP earned: {report.xp_earned}")
    _sub(f"Streak: {report.streak_days} day(s) (×{report.streak_multiplier})")
    _sub(f"Top apps: {report.app_breakdown}")

    print()
    for insight in report.insights:
        _sub(insight)

    # ── Done ─────────────────────────────────────────────────────────────
    _header("✅ Intelligence Layer — All Systems Operational")
    print()


if __name__ == "__main__":
    run_demo()
