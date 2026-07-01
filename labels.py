"""
Label Generator: maps confidence score to a tier and plain-language label text.

Thresholds (from planning.md):
  >= 0.75  → likely_ai
  <= 0.25  → likely_human
  else     → uncertain
"""

AI_THRESHOLD = 0.75
HUMAN_THRESHOLD = 0.25

LABEL_TEXT = {
    "likely_ai": (
        "This content shows strong indicators of AI generation. "
        "Our system is highly confident in this assessment."
    ),
    "likely_human": (
        "This content shows strong indicators of human authorship. "
        "Our system is highly confident in this assessment."
    ),
    "uncertain": (
        "This content shows some patterns associated with AI-generated text "
        "and patterns associated with human authorship. Our confidence is limited, "
        "and thus we cannot give a strong answer. The creator can request a review "
        "of this classification."
    ),
}


def generate_label(confidence: float) -> dict:
    if confidence >= AI_THRESHOLD:
        tier = "likely_ai"
    elif confidence <= HUMAN_THRESHOLD:
        tier = "likely_human"
    else:
        tier = "uncertain"

    return {"tier": tier, "text": LABEL_TEXT[tier]}
