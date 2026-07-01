"""
Full pipeline test: Signal A + Signal B + aggregator + confidence scoring.
Run: python test_scoring.py
"""

from signals.signal_a import score_with_groq
from signals.signal_b import score_stylometric_detailed
from aggregator import aggregate_scores
from confidence import calibrate_confidence
from labels import generate_label

SAMPLES = [
    ("Clearly AI",
     "Artificial intelligence represents a transformative paradigm shift in modern "
     "society. It is important to note that while the benefits of AI are numerous, "
     "it is equally essential to consider the ethical implications. Furthermore, "
     "stakeholders across various sectors must collaborate to ensure responsible deployment."),

    ("Clearly Human",
     "ok so i finally tried that new ramen place downtown and honestly? underwhelming. "
     "the broth was fine but they put WAY too much sodium in it and i was thirsty for "
     "like three hours after. my friend got the spicy version and said it was better. "
     "probably won't go back unless someone drags me there"),

    ("Borderline: formal human writing",
     "The relationship between monetary policy and asset price inflation has been "
     "extensively studied in the literature. Central banks face a fundamental tension "
     "between their mandate for price stability and the unintended consequences of "
     "prolonged low interest rates on equity and real estate valuations."),

    ("Borderline: lightly edited AI",
     "I've been thinking a lot about remote work lately. There are genuine tradeoffs — "
     "flexibility and no commute on one side, isolation and blurred work-life boundaries "
     "on the other. Studies show productivity varies widely by individual and role type."),
]

THRESHOLDS = {"likely_ai": 0.75, "likely_human": 0.25}

print("=" * 65)
print("Full Pipeline Test — Both Signals + Confidence Scoring")
print(f"Thresholds: likely_ai >= {THRESHOLDS['likely_ai']} | "
      f"likely_human <= {THRESHOLDS['likely_human']} | else: uncertain")
print("=" * 65)

for label, text in SAMPLES:
    print(f"\n[ {label} ]")

    score_a = score_with_groq(text)
    b_detail = score_stylometric_detailed(text)
    score_b = b_detail["signal_b"]

    agg = aggregate_scores(score_a, score_b)
    confidence = calibrate_confidence(agg["combined_score"], agg["disagreement"])
    result = generate_label(confidence)

    print(f"  Signal A (Groq LLM):      {score_a:.4f}")
    print(f"  Signal B (stylometric):   {score_b:.4f}")
    print(f"    | sent length variance: {b_detail['sentence_length_variance']:.4f}")
    print(f"    | avg sentence length:  {b_detail['average_sentence_length']:.4f}")
    print(f"    | avg word length:      {b_detail['average_word_length']:.4f}")
    print(f"    | ai transitions:       {b_detail['ai_transition_phrases']:.4f}")
    print(f"  Disagreement:             {agg['disagreement']:.4f}")
    print(f"  Combined score:           {agg['combined_score']:.4f}")
    print(f"  Confidence:               {confidence:.4f}")
    print(f"  Label tier:               {result['tier']}")

print("\n" + "=" * 65)
print("Threshold check (planning.md):")
print("  likely_ai   >= 0.75")
print("  likely_human <= 0.25")
print("  uncertain    0.26 – 0.74")
print("=" * 65)
