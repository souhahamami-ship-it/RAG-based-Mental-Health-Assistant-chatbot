"""
Pre-generation safety gate.

Design intent (see the accompanying review for the full rationale):
- This runs BEFORE any retrieval or LLM call. If it fires, we never send
  the user's message to the model or the knowledge base.
- It is a fast, cheap, first layer -- not the only layer. `check()` is the
  extension point for a second-pass classifier (a small model or a hosted
  moderation endpoint) for messages that are long, ambiguous, or borderline.
  That second pass is intentionally not implemented here: it depends on
  which provider/model you choose, and on clinical input into acceptable
  false-positive/false-negative rates. Do not ship this keyword-only
  version as your only safety layer in a real deployment.
- Every trip is logged via `logger` so it can be wired to an alerting/
  escalation channel. Nothing here decides *who* gets notified -- that's
  a product/clinical decision, not an engineering default.
"""

from __future__ import annotations

import logging
import re
import unicodedata

logger = logging.getLogger("mental_health_chatbot.safety")


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().strip()
    # Collapse repeated whitespace so "kill   myself" still matches, and
    # strip characters commonly used to break up filtered phrases.
    text = re.sub(r"[\s\-_.]+", " ", text)
    return text


class SafetyFilter:
    def __init__(self) -> None:
        # Kept as a plain list on purpose -- see module docstring on why
        # this is a first layer, not a complete solution.
        self._crisis_terms = [
            "suicide", "suicidal",
            "self harm", "self-harm", "selfharm",
            "kill myself", "killing myself",
            "end my life", "ending my life", "take my own life",
            "want to die", "wanna die",
            "don't want to live", "do not want to live",
            "don't want to be alive", "do not want to be alive",
            "wish i were dead", "wish i was dead", "wish i wasn't alive",
            "no reason to live", "no reason to keep going", "no point in living",
            "better off dead", "better off without me",
            "everyone would be better without me",
            "people would be better off without me",
            "just want everything to end", "want it all to end",
            "never wake up", "not wake up tomorrow",
            "done with life", "can't do this anymore", "cant do this anymore",
            "hurt myself", "harm myself",
            "hurt someone", "kill someone", "kill him", "kill her", "kill them",
        ]

    def check(self, text: str) -> bool:
        normalized = _normalize(text)
        for term in self._crisis_terms:
            if term in normalized:
                logger.warning("Crisis gate triggered (term class matched, content not logged)")
                return True
        return False

    @staticmethod
    def high_risk_response() -> str:
        return (
            "I'm really sorry you're going through this. "
            "If you think you might act on these thoughts, or you're in immediate danger, "
            "please contact your local emergency number or go to the nearest emergency department. "
            "If you can, stay with someone you trust and let them know you need support right now."
        )