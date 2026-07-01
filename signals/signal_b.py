"""
Signal B: Stylometric heuristics (pure Python).

Metrics (each normalized to [0.0, 1.0], where 1.0 = more AI-like):
  1. Sentence length variance  — low variance → AI
  2. Average sentence length   — longer sentences → AI
  3. Average word length       — longer words → AI (formal vocabulary)
  4. AI transition phrases     — more hits → AI

Returns a float in [0.0, 1.0].
"""

import re

_AI_TRANSITIONS = [
    "furthermore", "moreover", "additionally", "in conclusion",
    "it is important", "it is worth noting", "in summary", "to summarize",
    "notably", "it should be noted", "as a result", "consequently",
    "therefore", "in other words", "it is essential", "this demonstrates",
    "this highlights", "one can see", "it is clear", "stakeholders",
]


def _sentence_length_variance(sentences: list[str]) -> float:
    """Low variance → AI-like (returns value near 1.0)."""
    lengths = [len(s.split()) for s in sentences if s.strip()]
    if len(lengths) < 2:
        return 0.5
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    # Human variance typically >25; AI variance typically <10
    # Clamp at 50 so a single outlier sentence doesn't dominate
    return max(0.0, min(1.0, 1.0 - (variance / 50.0)))


def _average_sentence_length(sentences: list[str]) -> float:
    """Longer average sentence length → AI-like (returns value near 1.0)."""
    lengths = [len(s.split()) for s in sentences if s.strip()]
    if not lengths:
        return 0.5
    avg = sum(lengths) / len(lengths)
    # Casual human: ~6-12 words/sentence; AI: ~18-28 words/sentence
    # Map [6, 30] → [0.0, 1.0]
    return max(0.0, min(1.0, (avg - 6.0) / 24.0))


def _average_word_length(words: list[str]) -> float:
    """Longer average word length → AI-like formal vocabulary (returns value near 1.0)."""
    if not words:
        return 0.5
    avg = sum(len(w) for w in words) / len(words)
    # Casual human: ~3.5-4.5 chars; formal/AI: ~5.5-7.0 chars
    # Map [3.5, 7.0] → [0.0, 1.0]
    return max(0.0, min(1.0, (avg - 3.5) / 3.5))


def _ai_transition_score(text_lower: str) -> float:
    """Fraction of AI transition phrases detected (returns value near 1.0 for many hits)."""
    hits = sum(1 for phrase in _AI_TRANSITIONS if phrase in text_lower)
    # 4+ hits is a strong AI signal; scale accordingly
    return max(0.0, min(1.0, hits / 4.0))


def score_stylometric(text: str) -> float:
    """
    Compute stylometric heuristics and return a combined AI-confidence score
    in [0.0, 1.0].  Each sub-metric contributes equally (0.25 weight each).
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    words = re.findall(r"\b\w+\b", text.lower())
    text_lower = text.lower()

    slv = _sentence_length_variance(sentences)
    asl = _average_sentence_length(sentences)
    awl = _average_word_length(words)
    ait = _ai_transition_score(text_lower)

    combined = (slv + asl + awl + ait) / 4.0
    return round(combined, 4)


def score_stylometric_detailed(text: str) -> dict:
    """Same as score_stylometric but returns all sub-metric scores for inspection."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    words = re.findall(r"\b\w+\b", text.lower())
    text_lower = text.lower()

    slv = _sentence_length_variance(sentences)
    asl = _average_sentence_length(sentences)
    awl = _average_word_length(words)
    ait = _ai_transition_score(text_lower)

    return {
        "sentence_length_variance": round(slv, 4),
        "average_sentence_length": round(asl, 4),
        "average_word_length": round(awl, 4),
        "ai_transition_phrases": round(ait, 4),
        "signal_b": round((slv + asl + awl + ait) / 4.0, 4),
    }
