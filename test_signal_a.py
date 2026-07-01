"""
Standalone test for Signal A (Groq LLM classifier).
Run directly: python test_signal_a.py
"""

from signals.signal_a import score_with_groq

SAMPLES = [
    {
        "label": "AI-generated (GPT-style essay)",
        "text": (
            "Furthermore, it is important to note that artificial intelligence has "
            "significantly transformed modern society. Additionally, one can see that "
            "machine learning algorithms have consequently enabled new possibilities. "
            "Moreover, this demonstrates the remarkable capacity of neural networks to "
            "process information. In conclusion, it should be noted that these "
            "technologies will continue to evolve. Notably, the implications for various "
            "industries are substantial and far-reaching."
        ),
    },
    {
        "label": "Human-written (casual personal narrative)",
        "text": (
            "I wasn't sure what to write about today so I just started typing. My cat "
            "knocked over my coffee this morning—third time this week—and I spent twenty "
            "minutes cleaning the rug before I even had breakfast. I've been trying to "
            "get back into running but my knee's been giving me trouble since February. "
            "Maybe I should see someone about it. Anyway, I made it to the farmers "
            "market and got some really good strawberries."
        ),
    },
    {
        "label": "Ambiguous (edited human writing, grammar-polished)",
        "text": (
            "The committee reviewed the proposed changes and determined that several "
            "items required further clarification. Members expressed concern regarding "
            "the timeline and requested an updated schedule by the end of the quarter. "
            "All parties agreed to reconvene after the revised documentation had been "
            "circulated for review."
        ),
    },
]

if __name__ == "__main__":
    print("=" * 60)
    print("Signal A — Groq LLM Classifier Test")
    print("Model: llama-3.3-70b-versatile")
    print("Score: 0.0 = human  |  1.0 = AI-generated")
    print("=" * 60)

    for sample in SAMPLES:
        print(f"\nSample: {sample['label']}")
        print(f"Text:   {sample['text'][:80]}...")
        score = score_with_groq(sample["text"])
        print(f"Score:  {score:.4f}")

    print("\nDone.")
