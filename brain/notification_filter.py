"""
Track Shifter — Notification Filter
=====================================
Uses sentence-transformers (all-MiniLM-L6-v2) to decide whether an
incoming notification is semantically relevant to the user's current
study topic.  If the notification is relevant it is ALLOWed through
during focus; otherwise it is HELD until the session ends.

Dependencies:
    pip install sentence-transformers
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from config import BrainConfig, NotificationConfig


# ── Singleton model cache ────────────────────────────────────────────────────
# Loading the model is expensive (~250 MB), so we cache a single instance.

_MODEL_CACHE: Dict[str, SentenceTransformer] = {}


def _get_model(model_name: str) -> SentenceTransformer:
    """Return a cached SentenceTransformer instance."""
    if model_name not in _MODEL_CACHE:
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]


# ── Cosine similarity ───────────────────────────────────────────────────────

def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(vec_a, vec_b)
    norm = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


# ── Notification Filter ─────────────────────────────────────────────────────

class NotificationFilter:
    """
    Semantic notification filter powered by sentence-transformers.

    Converts the notification text and the current study topic into
    embeddings, computes cosine similarity, and compares against the
    configured threshold to decide ALLOW or HOLD.

    Usage::

        nf = NotificationFilter()                       # uses default config
        result = nf.evaluate(
            notification_text="Your AWS bill is ready",
            current_study_topic="Cloud computing and AWS services",
        )
        print(result)
        # {
        #   "notification": "Your AWS bill is ready",
        #   "similarity_score": 0.62,
        #   "decision": "ALLOW"
        # }
    """

    def __init__(self, config: Optional[BrainConfig] = None) -> None:
        self.config = config or BrainConfig()
        self._ncfg: NotificationConfig = self.config.notification
        self._model: SentenceTransformer = _get_model(self._ncfg.embedding_model)
        self._log: List[Dict[str, Any]] = []

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def log(self) -> List[Dict[str, Any]]:
        """Full history of evaluation results."""
        return list(self._log)

    def evaluate(
        self,
        notification_text: str,
        current_study_topic: str,
    ) -> Dict[str, Any]:
        """
        Decide whether a notification should interrupt focus.

        Args:
            notification_text:    the body / title of the notification
            current_study_topic:  what the user is currently studying

        Returns::

            {
                "notification": "<original text>",
                "similarity_score": <float 0-1>,
                "decision": "ALLOW" | "HOLD"
            }
        """
        # Encode both texts into embeddings
        embeddings = self._model.encode(
            [notification_text, current_study_topic],
            convert_to_numpy=True,
        )
        notif_vec = embeddings[0]
        topic_vec = embeddings[1]

        # Cosine similarity
        score = _cosine_similarity(notif_vec, topic_vec)
        score = round(score, 4)

        # Decision
        decision = "ALLOW" if score >= self._ncfg.relevance_threshold else "HOLD"

        result: Dict[str, Any] = {
            "notification": notification_text,
            "similarity_score": score,
            "decision": decision,
        }

        self._log.append(result)
        return result

    def evaluate_batch(
        self,
        notifications: List[str],
        current_study_topic: str,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple notifications at once (batched encoding).

        Args:
            notifications:        list of notification texts
            current_study_topic:  what the user is currently studying

        Returns:
            List of result dicts (same schema as ``evaluate``).
        """
        if not notifications:
            return []

        # Encode topic + all notifications in one batch
        all_texts = [current_study_topic] + notifications
        embeddings = self._model.encode(all_texts, convert_to_numpy=True)

        topic_vec = embeddings[0]
        results: List[Dict[str, Any]] = []

        for i, notif_text in enumerate(notifications):
            notif_vec = embeddings[i + 1]
            score = round(_cosine_similarity(notif_vec, topic_vec), 4)
            decision = "ALLOW" if score >= self._ncfg.relevance_threshold else "HOLD"

            entry: Dict[str, Any] = {
                "notification": notif_text,
                "similarity_score": score,
                "decision": decision,
            }
            results.append(entry)
            self._log.append(entry)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Summary statistics across all evaluated notifications."""
        total = len(self._log)
        allowed = sum(1 for r in self._log if r["decision"] == "ALLOW")
        held = total - allowed
        avg_score = (
            sum(r["similarity_score"] for r in self._log) / total
            if total
            else 0.0
        )
        return {
            "total_evaluated": total,
            "allowed": allowed,
            "held": held,
            "average_similarity": round(avg_score, 4),
        }
