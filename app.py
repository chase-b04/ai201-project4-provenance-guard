import uuid
import datetime
import concurrent.futures

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from signals.signal_a import score_with_groq
from signals.signal_b import score_stylometric
from aggregator import aggregate_scores
from confidence import calibrate_confidence
from labels import generate_label
from audit import log_entry, get_log, log_appeal, get_entry_by_content_id
from db import init_db, create_submission, get_submission, create_appeal

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

init_db()


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit_v1():
    body = request.get_json(silent=True)
    if not body or "text" not in body or "creator_id" not in body:
        return jsonify({"error": "Request body must include 'text' and 'creator_id' fields."}), 400

    text = body["text"]
    creator_id = body["creator_id"]
    content_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    # Run both signals concurrently (Signal A = network, Signal B = local)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(score_with_groq, text)
        future_b = executor.submit(score_stylometric, text)
        llm_score = future_a.result()
        stylometric_score = future_b.result()

    agg = aggregate_scores(llm_score, stylometric_score)
    confidence = calibrate_confidence(agg["combined_score"], agg["disagreement"])
    label = generate_label(confidence)

    entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": timestamp,
        "attribution": label["tier"],
        "label_text": label["text"],
        "confidence": confidence,
        "llm_score": llm_score,
        "stylometric_score": stylometric_score,
        "disagreement": agg["disagreement"],
        "appeal_filed": False,
        "status": "classified",
    }
    log_entry(entry)

    return jsonify(entry), 200


@app.route("/submissions", methods=["POST"])
@limiter.limit("10 per minute")
def submit():
    body = request.get_json(silent=True)
    if not body or "text" not in body:
        return jsonify({"error": "Request body must include a 'text' field."}), 400

    raw_text = body["text"]
    title = body.get("title", "")
    author = body.get("author", "")

    # Preprocessing
    from preprocessor import preprocess
    result = preprocess(raw_text)
    if not result["ok"]:
        return jsonify({"error": result["reason"]}), 422
    normalized = result["text"]

    submission_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    # Run both signals concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(score_with_groq, normalized)
        future_b = executor.submit(score_stylometric, normalized)
        score_a = future_a.result()
        score_b = future_b.result()

    aggregated = aggregate_scores(score_a, score_b)
    confidence = calibrate_confidence(aggregated["combined_score"], aggregated["disagreement"])
    label = generate_label(confidence)

    entry = {
        "submission_id": submission_id,
        "timestamp": timestamp,
        "title": title,
        "author": author,
        "signal_a": score_a,
        "signal_b": score_b,
        "aggregated_score": aggregated["combined_score"],
        "disagreement": aggregated["disagreement"],
        "confidence": confidence,
        "label_tier": label["tier"],
        "label_text": label["text"],
        "status": "reviewed",
    }

    create_submission(entry)
    log_entry(entry)

    return jsonify({
        "submission_id": submission_id,
        "attribution": label["tier"],
        "confidence": confidence,
        "label": label["text"],
        "signals": {"signal_a": score_a, "signal_b": score_b},
    }), 200


@app.route("/appeal", methods=["POST"])
def appeal():
    body = request.get_json(silent=True)
    if not body or "content_id" not in body or "creator_reasoning" not in body:
        return jsonify({"error": "Request body must include 'content_id' and 'creator_reasoning' fields."}), 400

    content_id = body["content_id"]
    creator_reasoning = body["creator_reasoning"]

    original = get_entry_by_content_id(content_id)
    if not original:
        return jsonify({"error": f"No submission found with content_id '{content_id}'."}), 404

    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    appeal_record = {
        "content_id": content_id,
        "creator_id": original.get("creator_id"),
        "creator_reasoning": creator_reasoning,
        "timestamp": timestamp,
        "original_attribution": original.get("attribution"),
        "original_confidence": original.get("confidence"),
        "original_llm_score": original.get("llm_score"),
        "original_stylometric_score": original.get("stylometric_score"),
        "status": "under_review",
    }
    log_appeal(appeal_record)

    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "message": "Appeal received. A human reviewer will evaluate your submission.",
    }), 200


@app.route("/log", methods=["GET"])
def log():
    return jsonify({"entries": get_log()}), 200


@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({"error": "Rate limit exceeded. Try again later."}), 429


if __name__ == "__main__":
    app.run(debug=True)
