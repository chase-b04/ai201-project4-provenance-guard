# ai201-project4-provenance-guard

Demo/Portfolio video: https://youtu.be/THCkp2k1tCU

# Architecture overview

A submission enters through POST /submit, which requires a text field and a creator_id. The request passes through Flask-Limiter first (10 requests/minute, 100/day per IP), and anything over the limit is rejected with a 429 before any processing happens.

If the request is within limits, the endpoint generates a unique content_id and timestamp, then runs both detection signals concurrently. Signal A makes a live call to Groq's llama-3.3-70b-versatile model with a structured prompt that returns a numeric AI-confidence score. Signal B runs locally in pure Python, computing four stylometric features: sentence length variance, average sentence length, average word length, and AI-associated transition phrase density. Because Signal A is a network call and Signal B is local computation, they run in parallel to reduce latency.

Both scores feed into the aggregator, which takes a weighted average (0.5 each). If the two signals disagree by more than 0.3, the combined score is pulled toward 0.5, reflecting that a split verdict should land in uncertain territory rather than drifting confidently in either direction. The calibration module applies a final smoothing pass before the confidence score is handed to the label generator.

The label generator maps the score to one of three tiers using fixed thresholds: 0.75 and above is "likely AI," 0.25 and below is "likely human," and everything in between is "uncertain." Each tier produces a specific plain-language label text. Before the response goes out, the full decision is written as an immutable entry to audit_log.json, capturing the content_id, both signal scores, the combined confidence, the attribution tier, the label text, and the status.

If a creator disputes the result, they submit to POST /appeal with their content_id and reasoning. The system looks up the original decision, appends an appeal entry to the audit log with the original signal scores alongside the creator's reasoning, and flips the submission's status to under_review for human review.

# Detection signals

Signal 1: LLM-based classifier (Groq, llama-3.3-70b-versatile)
What it measures: Semantic meaning, context, tone — holistic judgment. The model has been exposed to enormous amounts of both human and AI-generated text during training, so it has implicit pattern-recognition for things like generic phrasing, unnatural evenness, or hedging language that's hard to specify as an explicit rule.

Why I chose it: Why I chose it: A large language model is the only signal in this system that can read meaning. It catches things no hand-coded rule can, like generic phrasing, unnatural evenness, or hedging language that feels off but is hard to specify as an explicit statistic. Because the model has been trained on enormous amounts of both human and AI-generated text, it carries implicit pattern-recognition that would take thousands of hand-written rules to approximate. It also serves as a useful counterweight to Signal B: when the two signals disagree, that disagreement itself is informative.

What it misses: There is no clean, inspectable reason for its verdict the way there is with a heuristic, and it can be inconsistent across runs since the same text may get a slightly different score each time. It can also be steered by framing and does not capture structural or statistical features of the text at all.

Signal 2: Stylometric heuristics (pure Python)
What it measures: Statistical properties: sentence length variance, type-token ratio, punctuation density. Hand-built, fully explainable statistics computed directly from the text like sentence-length variance, average word length, punctuation patterns, and reliance on common AI-associated transition phrase.

Why I chose it: Stylometric features are fully explainable and completely deterministic. Every score can be traced back to a specific measurable property of the text, which makes this signal a useful complement to the LLM classifier. AI-generated text tends toward regularity: consistent sentence lengths, formal vocabulary, and heavy reliance on transition phrases. Human writing tends to be more irregular and inconsistent. This signal captures that surface-level difference without any API call or external dependency.

What it misses: Stylometric heuristics cannot read meaning at all, as it is only a counter. A children's book or a simple repetitive poem will score as AI-like because intentionally simple vocabulary and short repeated structures look statistically similar to generated text. A human piece that was run through a grammar tool may also trip this signal, since style editors smooth out the variance that makes writing look human to a heuristic.

# Confidence scoring

How signals are combined:
The two signal scores are averaged with equal weight (0.5 each). If the signals disagree by more than 0.3, the combined score is pulled toward 0.5 proportionally to the excess disagreement. This means a split verdict always lands in uncertain territory rather than drifting confidently in one direction. A final calibration pass applies a second soft pull toward 0.5 when disagreement is high, making the system less bold when the two signals conflict.

How I validated it is meaningful:
I ran all four test inputs from the scoring test through both signals separately before combining them, printing each sub-score individually to verify that neither signal was dominating or misbehaving. Signal B was recalibrated mid-development after the original metrics (type-token ratio and punctuation density) produced nearly identical scores across all inputs due to short text length. Replacing them with average sentence length and average word length produced scores that varied meaningfully across the test set. The final combined scores were checked against the planning thresholds manually before the scoring function was wired into the endpoint.

Example 1: High-confidence human
Input: casual ramen review ("ok so i finally tried that new ramen place...")

```json
{
  "llm_score": 0.2,
  "stylometric_score": 0.1298,
  "disagreement": 0.0702,
  "confidence": 0.1623,
  "attribution": "likely_human"
}
```

Both signals agree strongly. Low disagreement means no penalty is applied, and the confidence lands well below the 0.25 human threshold.

Example 2: Lower-confidence, uncertain result
Input: formal academic writing ("The relationship between monetary policy and asset price inflation...")

```json
{
  "llm_score": 0.8,
  "stylometric_score": 0.4338,
  "disagreement": 0.3662,
  "confidence": 0.5772,
  "attribution": "uncertain"
}
```

Signal A reads the formal register as AI-like. Signal B picks up long sentences and formal vocabulary but sees no transition phrases, so it is less convinced. The disagreement exceeds 0.3, triggering the penalty that pulls the combined score toward 0.5. The result is uncertain rather than a confident verdict in either direction, which is the intended behavior for a split case.

# Transparency label

likely_ai (confidence >= 0.75):
-"This content shows strong indicators of AI generation. Our system is highly confident in this assessment."

likely_human (confidence <= 0.25):
-"This content shows strong indicators of human authorship. Our system is highly confident in this assessment."

uncertain (confidence 0.26 to 0.74):
-"This content shows some patterns associated with AI-generated text and patterns associated with human authorship. Our confidence is limited, and thus we cannot give a strong answer. The creator can request a review of this classification."

# Rate limiting

Limit: 10 requests per minute, 100 requests per day per IP.

Reasoning: The 10 per minute figure reflects realistic single-user behavior. A writer submitting their own work for review is unlikely to need more than a few submissions in any given minute, so 10 is generous for legitimate use while still blocking a script that floods the endpoint in a tight loop. The 100 per day cap exists as a secondary backstop against sustained automated abuse that could stay just under the per-minute limit indefinitely. Both limits are applied at the IP level using Flask-Limiter with in-memory storage.

# Known limitations

The system will likely misclassify a children's book manuscript or any writing intentionally aimed at young readers. Short, repeated sentence structures and simple vocabulary are deliberate stylistic choices for that audience, but they look statistically identical to generated text on Signal B's metrics. Average sentence length will be low, word length will be short, and variance will be minimal, all of which push the stylometric score toward AI-generated. Signal A may partially correct for this if it reads the context correctly, but if the two signals disagree, the result lands in uncertain rather than correctly identifying the text as human. The system has no way to account for intentional simplicity as a craft choice.

# Spec reflection

One way the spec really helped me was giving exact word-for-word text for a lot of different parts, such as my labels and what the returns on the JSON from the API endpoints. One way I diverged from the spec was that my Signal B metrics were replaced mid-development. I at first kept the sentence length variance and token-type ratio and implemented them, but then switched it to average sentence length and average word length. The reason I did this was were the first two were returning nearly identical scores across all inputs, so changing my metrics allowed me to get better descrimination in my results.

# AI usage

Usage 1: I utilized Claude to generate my Flask app skeleton code with the POST /subit route stub for milestone 3. It generated mostly working and well designed code that followed my diagram and planning.md. What I did have to override was some of my initial Signal 1 logic when testing it.

Usage 2: I utilized Claude to implement my second function signal and my scoring logic for milestone 4. It generated code that followed my instructions, diagram, and planning.md. What I had to revise was my scoring logic and the metrics for my second signal.

Usage 3: I asked Claude to implement my label generation function that maps confidece scores to the correct label text and POST /appeal endpoint. It generated code that followed my instructions, diagram, and planning.md. What I had to revise was my appeal endpoint URL and my appead_filed flag to be set at submission test but never updated, which worked better for what I was going for for creating an easy experience for the user.

Usage 4: I used Claude to help me test by asking it to create test cases for me if the spec had not given me any and/or give me extras. It produced a mixture of powershell and cmd (vscode terminal) tests. What I did have to override was making all the powershell into cmd for my specific use case as well as using git bash for my rate limiting as my cmd test wasn't working.
