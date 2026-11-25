"""Conservative reference classifier for verification replies.

This module only classifies text. It does not submit verification, change
incident state, or treat silence as a reply. The backend owns verification
actions and timeouts; the Flutter client must preserve this behaviour.

Normalization is deliberately simple: Unicode NFKC, case folding, apostrophe
removal, punctuation-to-space conversion, and whitespace compaction. Negative
safety phrases are checked before positive phrases so that conflicting replies
remain negative.
"""

from __future__ import annotations

import enum
import re
import unicodedata
from typing import Tuple

__all__ = ["ReplyClassifier", "ReplyResult", "classify_reply"]


class ReplyResult(str, enum.Enum):
    OK = "ok"
    NOT_OK = "notOk"
    UNRECOGNISED = "unrecognised"


_POSITIVE_PHRASES: Tuple[str, ...] = (
    "im okay",
    "i am okay",
    "im ok",
    "i am ok",
    "im fine",
    "i am fine",
    "im safe",
    "i am safe",
)

_NEGATIVE_PHRASES: Tuple[str, ...] = (
    "im not okay",
    "im not ok",
    "i am not okay",
    "i am not ok",
    "not okay",
    "not ok",
    "not safe",
    "not fine",
    "i need help",
    "need help",
    "help me",
    "no i need help",
)


_APOSTROPHE_VARIANTS = str.maketrans("", "", "'\u2018\u2019\u02bb\u02bc`\u00b4")


def _normalize(reply: str) -> str:
    text = unicodedata.normalize("NFKC", reply).casefold()
    text = text.translate(_APOSTROPHE_VARIANTS)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def _contains_phrase(text: str, phrase: str) -> bool:
    return f" {phrase} " in f" {text} "


class ReplyClassifier:
    """Classify a verification reply as ``ok``, ``notOk`` or ``unrecognised``."""

    def classify(self, reply: str) -> ReplyResult:
        if not isinstance(reply, str):
            raise TypeError("reply must be a string")

        normalized = _normalize(reply)
        if not normalized:
            return ReplyResult.UNRECOGNISED

        if any(_contains_phrase(normalized, phrase) for phrase in _NEGATIVE_PHRASES):
            return ReplyResult.NOT_OK
        if any(_contains_phrase(normalized, phrase) for phrase in _POSITIVE_PHRASES):
            return ReplyResult.OK
        return ReplyResult.UNRECOGNISED


def classify_reply(reply: str) -> ReplyResult:
    """Convenience wrapper with no retained state."""

    return ReplyClassifier().classify(reply)
