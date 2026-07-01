"""
Signal Aggregator: weighted average with disagreement penalty.
"""

WEIGHT_A = 0.5
WEIGHT_B = 0.5
DISAGREEMENT_THRESHOLD = 0.3


def aggregate_scores(score_a: float, score_b: float) -> dict:
    combined = WEIGHT_A * score_a + WEIGHT_B * score_b
    disagreement = abs(score_a - score_b)

    # Pull combined score toward 0.5 when signals disagree significantly
    if disagreement > DISAGREEMENT_THRESHOLD:
        pull = (disagreement - DISAGREEMENT_THRESHOLD) * 0.5
        if combined > 0.5:
            combined -= pull
        else:
            combined += pull

    combined = round(max(0.0, min(1.0, combined)), 4)
    return {"combined_score": combined, "disagreement": round(disagreement, 4)}
