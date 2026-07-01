"""
Confidence Scoring Module: calibrate the aggregated score into a final
confidence value in [0.0, 1.0].
"""


def calibrate_confidence(combined_score: float, disagreement: float) -> float:
    """
    The aggregated score is already in [0.0, 1.0].  This module is the place
    for future calibration curves or smoothing.  For now it passes the score
    through with a minor smoothing step that compresses extreme values slightly
    when disagreement is high (making the system less bold when signals split).
    """
    confidence = combined_score

    if disagreement > 0.3:
        # Soft-pull toward 0.5 proportional to excess disagreement
        excess = disagreement - 0.3
        if confidence > 0.5:
            confidence -= excess * 0.1
        else:
            confidence += excess * 0.1

    return round(max(0.0, min(1.0, confidence)), 4)
