# Architecture Narrative

1. Submission Endpoint (POST /submissions)
   A creator or platform sends a piece of text (poem, story excerpt, blog post) to the submission endpoint, along with optional metadata like a title or author handle. This is the only public entry point for new content. Before anything else happens, the request passes through the Rate Limiter, which checks how many submissions this client (identified by API key or IP) has made in the current window. If they're over the limit, the request gets rejected immediately with a 429, and nothing downstream runs. If they're within limits, the request proceeds and gets a unique submission_id and timestamp.

2. Preprocessing
   The raw text is cleaned and normalized: stripping HTML if present, checking length bounds (too short to analyze, or too long for a single pass), and computing basic stats like word count. This isn't a signal in itself, it's just getting the text into a shape the detection pipeline can reliably work with.

3. Multi-Signal Detection Pipeline
   The normalized text is sent to Signal A by making an API call to Groq with a structured prompt asking for an attribution judgment, while Signal B runs locally and synchronously as pure Python computing the stylometric features. These can run concurrently since Signal A is a network call and Signal B is local computation, which is worth doing for latency.
   Tooling, throughout: Flask is the API framework handling routing and request/response, Flask-Limiter sits in front of the submission endpoint for rate limiting, and SQLite (or structured JSON, your call) is what the Audit Logger writes to at the end of each request and what GET /log reads from

4. Signal Aggregator
   The individual sub-scores from each detector get combined into one aggregate score using a weighted, calibrated combination function. This component also tracks which signals fired, with what strength, and whether they agreed or disagreed. Disagreement between signals is useful information on its own, since it feeds into how confident the final score should be.

5. Confidence Scoring Module
   The aggregator's combined score becomes a final confidence score (0.0 to 1.0), representing confidence that the content is AI-generated (or human-generated, depending on which way the score leans). This module is kept separate from the aggregator because its job is specifically calibration: making sure 0.95 really means "very sure" and 0.51 really means "barely leaning one way." Any score-smoothing, thresholding logic, or calibration curve testing lives here.

6. Classification + Label Generator
   The confidence score gets mapped into one of three label tiers (high-confidence AI, high-confidence human, uncertain) using fixed thresholds. The Label Generator then produces the actual plain-language text a reader would see, not just the tier name, but full sentences communicating the result and its confidence in non-technical language.

7. Audit Logger
   Before the response goes out, every detail of the decision gets written to the structured audit log as one immutable entry: submission ID, timestamp, raw signal scores, aggregated score, final confidence, label tier, label text. This happens regardless of outcome, so the log ends up as a complete record of every decision the system has ever made.

8. Response to Client
   The API returns the structured response: attribution result, confidence score, and transparency label text. This is what gets rendered to the end reader on the platform.

9. Appeals Workflow (a separate path, triggered later)
   If a creator disputes the label, they submit to a separate endpoint (POST /submissions/{id}/appeal) with their reasoning. This doesn't re-run detection. It creates an Appeal record linked to the original submission, sets that content's status to under_review, and writes a matching entry to the same audit log (appeal text, timestamp, link back to the original decision). A human reviewer is expected to act on it later; the system's job is just to capture and surface it, not resolve it automatically.

10. Audit Log Retrieval (GET /log)
    At any point, this endpoint returns the structured log entries, decisions and appeals together, so the full history of a piece of content (and the system's behavior in general) stays inspectable.

# Detection Signals:

Signal 1: LLM-based classifier (Groq, llama-3.3-70b-versatile)
What it measures: Semantic meaning, context, tone — holistic judgment. The model has been exposed to enormous amounts of both human and AI-generated text during training, so it has implicit pattern-recognition for things like generic phrasing, unnatural evenness, or hedging language that's hard to specify as an explicit rule.

Signal Output: prompting groq to return a numeric confidence rating directly as part of its structured response. That score comes back as a float, and we use it as-is after clamping it to the 0 to 1 range in case the model returns something slightly outside bounds.

Why it differs between human and AI writing: A large model has effectively absorbed millions of examples of what generated text tends to look like, since so much of the internet now contains it, and it can recognize stylistic tells that are hard to hand-code.

Blind spot: Can be steered by framing. Doesn't capture structure. We don't get a clean, inspectable reason for its judgment the way we do with a heuristic, and it can be inconsistent across runs since the same text might get a slightly different verdict each time the model is called.

Signal 2: Stylometric heuristics (pure Python)
What it measures: Statistical properties: sentence length variance, type-token ratio, punctuation density. Hand-built, fully explainable statistics computed directly from the text like sentence-length variance, average word length, punctuation patterns, and reliance on common AI-associated transition phrase.

Signal Output: Computes several individual metrics, normalizing each one against expected human and AI ranges, and averaging them into a single float. Each individual metric produces a small directional nudge and the average lands somewhere on the 0 to 1 scale.

Why it differs between human and AI writing: These metrics capture surface-level regularity. Models generate text that tends to reproduce patterns that were extremely common across its training data. Human writing tends to be more irregular. This signal is just counting things, which is exactly what makes it a useful complement to Signal A.

Blind spot: Can't read meaning. Human writers vary widely. Easy to fool deliberately and easy to trip by accident. A few sentence-length tweaks or a deliberate instruction can make AI text pass these heuristics cleanly, since the rules are simple and known.

Combining outputs: To combine them, the system takes a weighted average (0.5 each to start), then pulls the result toward 0.5 whenever the two signals disagree by more than 0.3, so a split verdict always lands in uncertain territory rather than drifting confidently in either direction.

# Uncertainty representation

What does a confidence score of 0.6 mean to your system?
-A confidence score of 0.6 in this system means the evidence leans toward one verdict but not by much, and is worth a second look by the reader.

How will you map raw signal outputs to a calibrated score?
-To get there, the raw outputs from Signal A and Signal B get normalized to a 0 to 1 scale each, then combined with a weighted average that gets pulled down whenever the two signals disagree, since disagreement is itself a sign that the case is murkier than either signal alone suggests.

What threshold separates "likely AI" from "uncertain" from "likely human"?
-I'm setting the thresholds at 0.75 and above for "likely AI," 0.25 and below for "likely human," and anything in between as "uncertain," with that uncertain band intentionally wide because the cost of a false confident verdict is higher than the cost of admitting we're not sure.

# Transparency label variants

What exact text will the label show for a high-confidence AI result?
-For the label text, the high-confidence AI variant reads: "This content shows strong indicators of AI generation. Our system is highly confident in this assessment."

A high-confidence human result?
-The high-confidence human variant reads: "This content shows strong indicators of human authorship. Our system is highly confident in this assessment."

An uncertain result?
-And the uncertain variant reads: "This content shows some patterns associated with AI-generated text and patterns associated with human authorship. Our confidence is limited, and thus we cannot give a strong answer. The creator can request a review of this classification."

# Appeals workflow and at least two anticipated edge cases

Who can submit an appeal?
-For appeals, only the original verified submitting creator can file one.

What information do they provide?
-They need to provide an explanation of why they believe the classification is wrong with reasoning in plain text

What does the system do when an appeal is received — what status changes, what gets logged?
-When an appeal comes in, the system logs the appeal text, a timestamp, and a reference back to the original decision (including its full signal breakdown), and flips the content's status from whatever it was to "under review."

What would a human reviewer see when they open the appeal queue?
-A human reviewer opening the appeal queue would see a list of pending appeals, each showing the original content, the original label and confidence score, the individual signal sub-scores that produced it, and the creator's appeal reasoning side by side, so they can judge the claim against the actual evidence rather than just the final verdict.

# Anticipated Edge Cases

What types of content will your system handle poorly? Name at least two specific scenarios — not generic risks like "inaccurate detection," but specific cases like "a poem with heavy use of repetition and simple vocabulary that your heuristics might score as AI-generated."

1. A children's book manuscript or simple repetitive poem written for young readers.
   -Will likely trip the stylometric signal toward "AI-generated," since intentionally simple vocabulary, short repeated sentence structures, and low lexical variety look statistically similar to generated text even though they're a deliberate human stylistic choice for the audience.
2. A piece of human writing that was run through a grammar or style tool.
   -These tools tend to smooth out sentence-length variance and standardize phrasing, could shift a genuinely human piece toward AI-like regularity on the stylometric signal even though no generation happened at all.

## Architecture

![alt text](<Submission Confidence-2026-06-30-193053-1.png>)

# SUBMISSION FLOW

Creator
|
| POST /submissions (raw text, metadata)
v
API Endpoint --> Rate Limiter --[exceeded]--> 429 Too Many Requests --> Client
|
[within limits]
|
v
Preprocessor
(clean, normalize, check bounds)
|
+-----------+-----------+
| Concurrent |
v v
Signal A: Groq Signal B: Stylometric
(API call, (pure Python,
llama-3.3-70b) local compute)
| |
+----------+------------+
|
v
Aggregator
(weighted avg + disagreement penalty)
|
v
Confidence Scorer
(calibrate 0.0-1.0)
|
v
Label Generator
(map to tier, generate label text)
|
v
Audit Logger
(write immutable entry to SQLite/JSON)
|
v
200 OK --> Client
(attribution result, confidence, label text)

# APPEAL FLOW

Creator
|
| POST /submissions/{id}/appeal (reasoning)
v
API Endpoint
|
+--> Create Appeal record (link to submission)
+--> Set status to "under_review"
|
v
Audit Logger
(write appeal entry: text, timestamp, link to original decision)
|
v
200 OK --> Creator
(appeal received, awaiting review)

On submission, a piece of text enters through the API endpoint, clears the rate limiter, gets cleaned by the preprocessor, and then passes to both signals concurrently: Signal A makes a live call to Groq while Signal B computes stylometric features locally in Python. Their scores flow into the aggregator, get calibrated into a final confidence score, mapped to a label tier, and written to the audit log before the result is returned to the client. On appeal, a creator posts their reasoning to a separate endpoint, which creates an appeal record linked to the original decision, flips the content's status to "under review," and writes a full appeal entry to the same audit log, at which point the case sits in the review queue for a human to evaluate.

# AI Tool usage

M3: I will provide Claude my planning.md (detection signal section) and diagram to generate the Flask app skeleton code + the first signal function. I will verify the output by testing a few inputs directly before and after wiring the endpoint.

M4: I will provide Claude my planning.md (detection signal section and uncertainty representation) and diagram to generate the second signal function and scoring logic. I do multiple checks on both signal functions, scoring logic, and combined scores to make sure the program is fully working and can tell the differences between human and AI text.

M5: I will provide Claude my planning.md (label variants + appeals workflow) and diagram to generate the label generation logic, /appeal endpoint, and any more logic needed for a smooth program and working interface. I will test and verify my code by testing all three labels, making sure they are reachable, and that an appeal updates status correctly.
