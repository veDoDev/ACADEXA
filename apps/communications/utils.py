from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModerationResult:
    is_flagged: bool
    flag_reason: str
    sentiment_label: str
    sentiment_score: int


_BAD_WORDS = [
    "abuse",
    "cheat",
    "threat",
    "hate",
    "stupid",
    "idiot",
    "fail you",
]

_POSITIVE = [
    "thanks",
    "thank you",
    "great",
    "good job",
    "well done",
    "awesome",
    "nice",
]

_NEGATIVE = [
    "angry",
    "upset",
    "worst",
    "terrible",
    "useless",
    "bad",
    "pathetic",
]


def keyword_moderate_and_sentiment(text: str) -> ModerationResult:
    """A lightweight stand-in for Gemini sentiment/moderation.

    Keeps behavior deterministic for demos and works offline.
    """
    body_lower = (text or "").lower()

    # Moderation
    for word in _BAD_WORDS:
        if word in body_lower:
            return ModerationResult(
                is_flagged=True,
                flag_reason=f"Contains flagged keyword: '{word}'",
                sentiment_label="negative",
                sentiment_score=-60,
            )

    pos_hits = sum(1 for w in _POSITIVE if w in body_lower)
    neg_hits = sum(1 for w in _NEGATIVE if w in body_lower)

    score = (pos_hits - neg_hits) * 25
    if score > 100:
        score = 100
    if score < -100:
        score = -100

    if score >= 25:
        label = "positive"
    elif score <= -25:
        label = "negative"
    else:
        label = "neutral"

    return ModerationResult(
        is_flagged=False,
        flag_reason="",
        sentiment_label=label,
        sentiment_score=score,
    )
