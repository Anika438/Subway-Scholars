"""
Track Shifter — Navigator AI
=============================
Parses a .ics calendar file and recommends optimal focus windows
(sprint and marathon) based on free-time gaps, deadline proximity,
and the user's preferred productivity time-of-day.

Dependencies:
    pip install ics
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, time as dt_time
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple

from ics import Calendar, Event


# ── Constants ────────────────────────────────────────────────────────────────

SPRINT_MINUTES = 25
MARATHON_MINUTES = 90

PREFERENCE_HOURS: Dict[str, Tuple[int, int]] = {
    "morning":   (6, 12),
    "afternoon": (12, 17),
    "evening":   (17, 22),
}


class EnergyMode(Enum):
    """Energy level derived from sleep duration."""
    HIGH = "HIGH"       # >= 7 hours
    MEDIUM = "MEDIUM"   # 5-7 hours
    LOW = "LOW"         # < 5 hours


def _compute_sleep_duration(sleep_hours: Tuple[int, int]) -> float:
    """
    Calculate how many hours the user actually slept.

    sleep_hours is (bed_hour, wake_hour), e.g. (23, 7) → 8 h.
    """
    bed, wake = sleep_hours
    if bed > wake:
        return 24 - bed + wake
    elif bed == wake:
        return 0.0
    else:
        return wake - bed


def _energy_mode_from_sleep(sleep_hours: Tuple[int, int]) -> EnergyMode:
    """Map sleep duration to an EnergyMode."""
    duration = _compute_sleep_duration(sleep_hours)
    if duration >= 7:
        return EnergyMode.HIGH
    elif duration >= 5:
        return EnergyMode.MEDIUM
    else:
        return EnergyMode.LOW

# ── Data helpers ─────────────────────────────────────────────────────────────


def _time_str(dt: datetime) -> str:
    """Format a datetime as HH:MM."""
    return dt.strftime("%H:%M")


def _sleep_window(
    current_date: datetime,
    sleep_hours: Tuple[int, int],
) -> Tuple[datetime, datetime]:
    """
    Return (sleep_start, sleep_end) for the given date.

    sleep_hours is a tuple like (23, 7) meaning 11 PM → 7 AM.
    If the start hour > end hour we assume the window crosses midnight.
    """
    s_start, s_end = sleep_hours
    sleep_start = current_date.replace(hour=s_start, minute=0, second=0, microsecond=0)
    sleep_end = current_date.replace(hour=s_end, minute=0, second=0, microsecond=0)
    if s_start > s_end:
        # crosses midnight — sleep_end is the next morning
        sleep_end += timedelta(days=1)
    return sleep_start, sleep_end


# ── Gap scoring ──────────────────────────────────────────────────────────────


def _score_gap(
    gap_start: datetime,
    gap_end: datetime,
    deadlines: List[datetime],
    pref_range: Tuple[int, int],
) -> float:
    """
    Score a free-time gap (higher is better).

    Factors:
      1. Duration — longer gaps score higher (diminishing returns above 90 min)
      2. Deadline proximity — gaps right before a deadline event score higher
      3. Time-of-day alignment — gaps inside the user's preferred hours score higher
    """
    duration_min = (gap_end - gap_start).total_seconds() / 60

    # 1 — duration score (0-40 pts, log-ish curve capped at 90 min)
    dur_score = min(duration_min, 90) / 90 * 40

    # 2 — deadline proximity (0-30 pts)
    deadline_score = 0.0
    for dl in deadlines:
        hours_until = (dl - gap_end).total_seconds() / 3600
        if 0 < hours_until <= 24:
            # the closer to the deadline, the higher the boost
            deadline_score = max(deadline_score, 30 * (1 - hours_until / 24))

    # 3 — time-of-day preference (0-30 pts)
    pref_start, pref_end = pref_range
    mid_hour = (gap_start + (gap_end - gap_start) / 2).hour
    if pref_start <= mid_hour < pref_end:
        pref_score = 30.0
    elif abs(mid_hour - pref_start) <= 1 or abs(mid_hour - pref_end) <= 1:
        pref_score = 15.0  # adjacent hour — partial credit
    else:
        pref_score = 0.0

    return dur_score + deadline_score + pref_score


# ── Core navigator ──────────────────────────────────────────────────────────


class Navigator:
    """
    Parses a .ics calendar file and recommends focus windows.

    Usage::

        nav = Navigator(
            path_to_ics_file="calendar.ics",
            sleep_hours=(23, 7),
            productivity_preference="morning",
            current_date=datetime(2026, 2, 28),
        )
        result = nav.recommend()
    """

    def __init__(
        self,
        path_to_ics_file: str,
        sleep_hours: Tuple[int, int] = (23, 7),
        productivity_preference: str = "morning",
        current_date: Optional[datetime] = None,
    ) -> None:
        self.ics_path = path_to_ics_file
        self.sleep_hours = sleep_hours
        self.preference = productivity_preference.lower()
        self.current_date = current_date or datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0,
        )

        if self.preference not in PREFERENCE_HOURS:
            raise ValueError(
                f"productivity_preference must be one of {list(PREFERENCE_HOURS)}, "
                f"got '{self.preference}'"
            )

        self.energy_mode: EnergyMode = _energy_mode_from_sleep(self.sleep_hours)
        self.sleep_duration: float = _compute_sleep_duration(self.sleep_hours)

        self._events: List[Event] = []
        self._parse_calendar()

    # ── Calendar parsing ─────────────────────────────────────────────────

    def _parse_calendar(self) -> None:
        """Read and filter .ics events for the target date."""
        if not os.path.isfile(self.ics_path):
            raise FileNotFoundError(f"Calendar file not found: {self.ics_path}")

        with open(self.ics_path, "r", encoding="utf-8") as f:
            cal = Calendar(f.read())

        day_start = self.current_date
        day_end = day_start + timedelta(days=1)

        for event in cal.events:
            evt_start = event.begin.datetime if hasattr(event.begin, 'datetime') else event.begin
            evt_end = event.end.datetime if hasattr(event.end, 'datetime') else event.end

            # Ensure naive datetimes for comparison
            if hasattr(evt_start, 'tzinfo') and evt_start.tzinfo is not None:
                evt_start = evt_start.replace(tzinfo=None)
            if hasattr(evt_end, 'tzinfo') and evt_end.tzinfo is not None:
                evt_end = evt_end.replace(tzinfo=None)

            # Keep events that overlap with the target day
            if evt_start < day_end and evt_end > day_start:
                self._events.append(event)

        # Sort by start time
        self._events.sort(key=lambda e: (
            e.begin.datetime.replace(tzinfo=None)
            if hasattr(e.begin, 'datetime')
            else e.begin.replace(tzinfo=None)
            if hasattr(e.begin, 'tzinfo') and e.begin.tzinfo is not None
            else e.begin
        ))

    # ── Free-gap computation ─────────────────────────────────────────────

    def _get_busy_blocks(self) -> List[Tuple[datetime, datetime]]:
        """Return sorted, merged busy blocks for the target day."""
        blocks: List[Tuple[datetime, datetime]] = []

        for event in self._events:
            start = event.begin.datetime if hasattr(event.begin, 'datetime') else event.begin
            end = event.end.datetime if hasattr(event.end, 'datetime') else event.end

            if hasattr(start, 'tzinfo') and start.tzinfo is not None:
                start = start.replace(tzinfo=None)
            if hasattr(end, 'tzinfo') and end.tzinfo is not None:
                end = end.replace(tzinfo=None)

            blocks.append((start, end))

        # Add sleep window as a busy block
        sl_start, sl_end = _sleep_window(self.current_date, self.sleep_hours)
        # Sleep may span two calendar days — split if needed
        day_start = self.current_date
        day_end = day_start + timedelta(days=1)

        # Early-morning sleep (e.g. 00:00-07:00 from previous night)
        if self.sleep_hours[0] > self.sleep_hours[1]:
            early_end = self.current_date.replace(
                hour=self.sleep_hours[1], minute=0, second=0, microsecond=0,
            )
            blocks.append((day_start, early_end))
            late_start = self.current_date.replace(
                hour=self.sleep_hours[0], minute=0, second=0, microsecond=0,
            )
            blocks.append((late_start, day_end))
        else:
            blocks.append((sl_start, sl_end))

        # Sort and merge overlapping blocks
        blocks.sort(key=lambda b: b[0])
        merged: List[Tuple[datetime, datetime]] = []
        for start, end in blocks:
            # Clamp to the day
            start = max(start, day_start)
            end = min(end, day_end)
            if start >= end:
                continue
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        return merged

    def _get_free_gaps(self) -> List[Tuple[datetime, datetime]]:
        """Identify free-time gaps between busy blocks."""
        busy = self._get_busy_blocks()
        day_start = self.current_date
        day_end = day_start + timedelta(days=1)

        gaps: List[Tuple[datetime, datetime]] = []
        cursor = day_start

        for blk_start, blk_end in busy:
            if cursor < blk_start:
                gaps.append((cursor, blk_start))
            cursor = max(cursor, blk_end)

        if cursor < day_end:
            gaps.append((cursor, day_end))

        return gaps

    # ── Deadline extraction ──────────────────────────────────────────────

    def _get_deadlines(self) -> List[datetime]:
        """
        Extract deadline-like events (heuristic: events whose name contains
        deadline / due / submit / exam keywords).
        """
        keywords = {"deadline", "due", "submit", "exam", "test", "assignment", "final"}
        deadlines: List[datetime] = []

        for event in self._events:
            name = (event.name or "").lower()
            if any(kw in name for kw in keywords):
                evt_start = event.begin.datetime if hasattr(event.begin, 'datetime') else event.begin
                if hasattr(evt_start, 'tzinfo') and evt_start.tzinfo is not None:
                    evt_start = evt_start.replace(tzinfo=None)
                deadlines.append(evt_start)

        return deadlines

    # ── Recommendation engine ────────────────────────────────────────────

    def recommend(self) -> Dict[str, Any]:
        """
        Return recommended focus windows, adapted to the user's energy
        level (derived from sleep duration).

        Energy modes:
            HIGH   (>= 7 h sleep): 1 marathon (90 min) + 2 sprints (25 min)
            MEDIUM (5-7 h sleep):  3 sprints; marathon only if a high-scoring
                                   long gap exists
            LOW    (< 5 h sleep):  4 short sprints; NO marathon;
                                   prefer gaps near deadlines

        Returns::

            {
                "energy_mode": "HIGH" | "MEDIUM" | "LOW",
                "sleep_hours": <float>,
                "recommended_sprints": [
                    {"start": "HH:MM", "end": "HH:MM"}, ...
                ],
                "marathon": {"start": "HH:MM", "end": "HH:MM"} | null
            }
        """
        gaps = self._get_free_gaps()
        deadlines = self._get_deadlines()
        pref_range = PREFERENCE_HOURS[self.preference]
        mode = self.energy_mode

        # ── Decide sprint / marathon quotas ──────────────────────────────
        if mode == EnergyMode.HIGH:
            max_sprints = 2
            allow_marathon = True
            marathon_must_be_top = False   # always include if gap exists
        elif mode == EnergyMode.MEDIUM:
            max_sprints = 3
            allow_marathon = True
            marathon_must_be_top = True    # only if gap scores very high
        else:  # LOW
            max_sprints = 4
            allow_marathon = False
            marathon_must_be_top = False

        # ── Score every gap ──────────────────────────────────────────────
        scored: List[Tuple[float, datetime, datetime]] = []
        for g_start, g_end in gaps:
            gap_minutes = (g_end - g_start).total_seconds() / 60
            if gap_minutes < SPRINT_MINUTES:
                continue  # too short for any focus window
            score = _score_gap(g_start, g_end, deadlines, pref_range)

            # LOW energy: boost deadline-adjacent gaps, penalise long ones
            if mode == EnergyMode.LOW:
                # Extra deadline weight
                dl_bonus = 0.0
                for dl in deadlines:
                    hrs = (dl - g_end).total_seconds() / 3600
                    if 0 < hrs <= 12:
                        dl_bonus = max(dl_bonus, 20 * (1 - hrs / 12))
                score += dl_bonus
                # Penalise gaps longer than 60 min (discourage long blocks)
                if gap_minutes > 60:
                    score -= 10

            scored.append((score, g_start, g_end))

        scored.sort(key=lambda x: -x[0])  # highest score first

        # ── Pick sprints ─────────────────────────────────────────────────
        sprints: List[Dict[str, str]] = []
        used_intervals: List[Tuple[datetime, datetime]] = []

        for _score, g_start, g_end in scored:
            if len(sprints) >= max_sprints:
                break
            gap_min = (g_end - g_start).total_seconds() / 60
            if gap_min < SPRINT_MINUTES:
                continue

            # Place sprint at the start of the gap
            s_start = g_start
            s_end = g_start + timedelta(minutes=SPRINT_MINUTES)

            # Check overlap with already-selected intervals
            overlaps = any(
                s_start < u_end and s_end > u_start
                for u_start, u_end in used_intervals
            )
            if overlaps:
                continue

            sprints.append({"start": _time_str(s_start), "end": _time_str(s_end)})
            used_intervals.append((s_start, s_end))

            # Fill more sprints from the same gap if room remains
            cursor = s_end + timedelta(minutes=5)  # 5-min buffer
            while len(sprints) < max_sprints:
                remaining_min = (g_end - cursor).total_seconds() / 60
                if remaining_min < SPRINT_MINUTES:
                    break
                sprints.append({
                    "start": _time_str(cursor),
                    "end": _time_str(cursor + timedelta(minutes=SPRINT_MINUTES)),
                })
                used_intervals.append((
                    cursor,
                    cursor + timedelta(minutes=SPRINT_MINUTES),
                ))
                cursor = cursor + timedelta(minutes=SPRINT_MINUTES + 5)

        # Sort sprints chronologically
        sprints.sort(key=lambda s: s["start"])

        # ── Pick marathon ────────────────────────────────────────────────
        marathon: Optional[Dict[str, str]] = None

        if allow_marathon:
            # For MEDIUM mode, only include marathon if top-scored gap
            # is long enough (score must be in the top 50 %)
            score_threshold = 0.0
            if marathon_must_be_top and scored:
                all_scores = [s[0] for s in scored]
                score_threshold = sorted(all_scores, reverse=True)[
                    max(0, len(all_scores) // 2 - 1)
                ]

            for gap_score, g_start, g_end in scored:
                gap_min = (g_end - g_start).total_seconds() / 60
                if gap_min < MARATHON_MINUTES:
                    continue
                if marathon_must_be_top and gap_score < score_threshold:
                    continue
                marathon = {
                    "start": _time_str(g_start),
                    "end": _time_str(g_start + timedelta(minutes=MARATHON_MINUTES)),
                }
                break

        # ── Assemble output ──────────────────────────────────────────────
        result: Dict[str, Any] = {
            "energy_mode": mode.value,
            "sleep_hours": round(self.sleep_duration, 1),
            "recommended_sprints": sprints[:max_sprints],
            "marathon": marathon,
        }

        return result


# ── Convenience function ─────────────────────────────────────────────────────

def get_focus_windows(
    path_to_ics_file: str,
    sleep_hours: Tuple[int, int] = (23, 7),
    productivity_preference: str = "morning",
    current_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    One-call convenience wrapper.

    Args:
        path_to_ics_file: path to a .ics calendar file
        sleep_hours: tuple (bed_hour, wake_hour), e.g. (23, 7) → 8 h → HIGH
        productivity_preference: "morning" | "afternoon" | "evening"
        current_date: date to analyse (defaults to today)

    Returns:
        Dict with ``energy_mode``, ``sleep_hours``,
        ``recommended_sprints``, and ``marathon`` keys.
    """
    nav = Navigator(
        path_to_ics_file=path_to_ics_file,
        sleep_hours=sleep_hours,
        productivity_preference=productivity_preference,
        current_date=current_date,
    )
    return nav.recommend()
