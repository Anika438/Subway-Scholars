"""
Notification Monitor — Intercepts Windows toast notifications during focus sessions.

Study / work-relevant notifications pass through untouched.
Irrelevant ones are dismissed from the notification centre and stored for a
post-session recap.

Requires:  pip install winsdk
Falls back gracefully if winsdk is missing or the user denies listener access.
"""

import asyncio
import os
import sys
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Try importing the Windows SDK notification APIs
# ---------------------------------------------------------------------------
try:
    from winsdk.windows.ui.notifications.management import (
        UserNotificationListener,
        UserNotificationListenerAccessStatus,
    )
    from winsdk.windows.ui.notifications import (
        KnownNotificationBindings,
        NotificationKinds,
    )

    WINSDK_AVAILABLE = True
except ImportError:
    WINSDK_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data model for a held (suppressed) notification
# ---------------------------------------------------------------------------
class HeldNotification:
    """A notification that was deemed irrelevant and removed from the tray."""

    def __init__(
        self,
        app_name: str,
        title: str,
        body: str,
        timestamp: datetime,
        notification_id: int = 0,
    ):
        self.app_name = app_name
        self.title = title
        self.body = body
        self.timestamp = timestamp
        self.notification_id = notification_id

    def to_dict(self) -> Dict:
        return {
            "app_name": self.app_name,
            "title": self.title,
            "body": self.body,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Main monitor class
# ---------------------------------------------------------------------------
class NotificationMonitor:
    """
    Polls Windows toast notifications every few seconds.
    New notifications are classified by an AI filter function:
      - relevant  →  left in the notification centre
      - irrelevant →  dismissed + held for recap
    """

    def __init__(
        self,
        filter_fn: Optional[Callable[[str, str], bool]] = None,
        on_notification_held: Optional[Callable[[Dict], None]] = None,
    ):
        """
        Parameters
        ----------
        filter_fn : callable(notification_text, current_topic) -> bool
            Return True to *allow* the notification, False to *hold* it.
        on_notification_held : callable(held_notification_dict) -> None
            Fired every time a notification is held (for live WS broadcast).
        """
        self.filter_fn = filter_fn
        self.on_notification_held = on_notification_held
        self.held_notifications: List[HeldNotification] = []
        self._seen_ids: set = set()
        self.is_running = False
        self.current_topic = "General Study"
        self._thread: Optional[threading.Thread] = None
        self._listener = None
        self._access_granted = False

    # ── Async initialisation ────────────────────────────────────────

    async def _init_listener(self):
        if not WINSDK_AVAILABLE:
            print(
                "[NotifMonitor] winsdk not installed — notification filtering disabled.",
                flush=True,
            )
            return
        try:
            self._listener = UserNotificationListener.current
            status = await self._listener.request_access_async()
            if status == UserNotificationListenerAccessStatus.ALLOWED:
                self._access_granted = True
                print("[NotifMonitor] Listener access GRANTED.", flush=True)
            else:
                print(
                    f"[NotifMonitor] Listener access DENIED ({status}). "
                    "Enable in Settings → Notifications → Notification access.",
                    flush=True,
                )
        except Exception as exc:
            print(f"[NotifMonitor] Listener init error: {exc}", flush=True)

    async def _snapshot_existing(self):
        """Record IDs of already-present notifications so only NEW ones are filtered."""
        if not self._access_granted:
            return
        try:
            notifs = await self._listener.get_notifications_async(
                NotificationKinds.TOAST
            )
            for n in notifs:
                self._seen_ids.add(n.id)
            print(
                f"[NotifMonitor] Snapshot: {len(self._seen_ids)} pre-existing notifications.",
                flush=True,
            )
        except Exception as exc:
            print(f"[NotifMonitor] Snapshot error: {exc}", flush=True)

    # ── Polling ─────────────────────────────────────────────────────

    async def _poll_once(self):
        if not self._access_granted or not self._listener:
            return
        try:
            notifs = await self._listener.get_notifications_async(
                NotificationKinds.TOAST
            )
            for n in notifs:
                nid = n.id
                if nid in self._seen_ids:
                    continue
                self._seen_ids.add(nid)

                app_name, title, body = self._extract_text(n)
                full_text = f"{app_name}: {title} {body}".strip()
                if not full_text or full_text in (":", "Unknown:"):
                    continue

                # --- AI classification ---
                is_relevant = True
                if self.filter_fn:
                    try:
                        is_relevant = self.filter_fn(full_text, self.current_topic)
                    except Exception as exc:
                        print(f"[NotifMonitor] Filter error: {exc}", flush=True)
                        is_relevant = False

                if is_relevant:
                    print(f"[NotifMonitor] ALLOWED: {full_text[:90]}", flush=True)
                else:
                    held = HeldNotification(
                        app_name=app_name,
                        title=title,
                        body=body,
                        timestamp=datetime.now(),
                        notification_id=nid,
                    )
                    self.held_notifications.append(held)

                    # Dismiss from the notification centre
                    try:
                        self._listener.remove_notification(nid)
                    except Exception:
                        pass

                    print(f"[NotifMonitor] HELD: {full_text[:90]}", flush=True)

                    # Live callback (used for WebSocket broadcast)
                    if self.on_notification_held:
                        try:
                            self.on_notification_held(held.to_dict())
                        except Exception:
                            pass
        except Exception as exc:
            print(f"[NotifMonitor] Poll error: {exc}", flush=True)

    # ── Text extraction helpers ─────────────────────────────────────

    @staticmethod
    def _extract_text(notif):
        """Pull app name, title, and body out of a UserNotification object."""
        app_name = "Unknown"
        title = ""
        body = ""
        try:
            if notif.app_info and notif.app_info.display_info:
                app_name = notif.app_info.display_info.display_name or "Unknown"
        except Exception:
            pass
        try:
            binding = notif.notification.visual.get_binding(
                KnownNotificationBindings.toast_generic
            )
            if binding:
                texts = [el.text for el in binding.get_text_elements()]
                if texts:
                    title = texts[0]
                if len(texts) > 1:
                    body = " ".join(texts[1:])
        except Exception:
            pass
        return app_name, title, body

    # ── Background thread ───────────────────────────────────────────

    def _run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._init_listener())
        if self._access_granted:
            loop.run_until_complete(self._snapshot_existing())
        while self.is_running:
            if self._access_granted:
                loop.run_until_complete(self._poll_once())
            time.sleep(3)
        loop.close()

    # ── Public API ──────────────────────────────────────────────────

    def start(self, topic: str = "General Study"):
        """Begin monitoring notifications for a focus session."""
        if self.is_running:
            self.update_topic(topic)
            return
        self.current_topic = topic
        self.is_running = True
        self._seen_ids.clear()
        self._access_granted = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[NotifMonitor] Started — topic: {topic}", flush=True)

    def stop(self):
        """Stop monitoring (end of focus session)."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        print(
            f"[NotifMonitor] Stopped. {len(self.held_notifications)} notifications held.",
            flush=True,
        )

    def update_topic(self, topic: str):
        self.current_topic = topic

    def get_held(self) -> List[Dict]:
        """Return all held notifications as serialisable dicts."""
        return [n.to_dict() for n in self.held_notifications]

    def clear_held(self) -> int:
        """Clear held notifications (after user reviews recap). Returns count cleared."""
        count = len(self.held_notifications)
        self.held_notifications.clear()
        return count

    @property
    def held_count(self) -> int:
        return len(self.held_notifications)
