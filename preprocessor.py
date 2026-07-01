import re
import html

MIN_WORDS = 20
MAX_WORDS = 5000


def preprocess(raw_text: str) -> dict:
    # Unescape HTML entities then strip tags
    text = html.unescape(raw_text)
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    word_count = len(text.split())
    if word_count < MIN_WORDS:
        return {"ok": False, "reason": f"Text too short (minimum {MIN_WORDS} words)."}
    if word_count > MAX_WORDS:
        return {"ok": False, "reason": f"Text too long (maximum {MAX_WORDS} words)."}

    return {"ok": True, "text": text, "word_count": word_count}
