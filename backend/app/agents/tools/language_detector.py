"""
Language detection tool.
Uses rule-based heuristics first (fast, no API call), falls back to Gemini
for ambiguous text.
Returns ISO 639-1 language codes (e.g. "en", "es", "fr").
"""
import re
import logging
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# Character range heuristics
_CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7ff]")
_ARABIC = re.compile(r"[\u0600-\u06ff]")
_CYRILLIC = re.compile(r"[\u0400-\u04ff]")
_LATIN_EXTENDED = re.compile(r"[áéíóúüñ¿¡àèìòùâêîôûçœæ]", re.IGNORECASE)

# Common Spanish stop-words (quick heuristic)
_ES_STOPWORDS = {"el", "la", "los", "las", "es", "en", "de", "que", "un", "una",
                 "por", "para", "con", "del", "al", "se", "su", "como", "más",
                 "pero", "cuando", "cuál", "cuáles", "qué", "cómo"}


def detect_language(text: str) -> str:
    """Return an ISO 639-1 code for the dominant language of *text*."""
    sample = text[:500].lower()
    words = set(re.findall(r"\b\w+\b", sample))

    # Script-based detection (fast path)
    if _CJK.search(sample):
        return "zh"
    if _ARABIC.search(sample):
        return "ar"
    if _CYRILLIC.search(sample):
        return "ru"

    # Spanish heuristics
    if _LATIN_EXTENDED.search(sample) or len(words & _ES_STOPWORDS) >= 2:
        return "es"

    # If text is clearly ASCII-only with common English patterns, return "en"
    english_indicators = {"the", "is", "are", "was", "were", "this", "that",
                          "and", "or", "but", "with", "for", "from", "have"}
    if len(words & english_indicators) >= 2:
        return "en"

    # Fall back to Gemini for ambiguous cases
    return _llm_detect(text[:200])


def _llm_detect(text: str) -> str:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    prompt = (
        "Identify the language of the following text. "
        "Reply with ONLY the ISO 639-1 two-letter language code (e.g. 'en', 'es', 'fr', 'de'). "
        "No explanation.\n\n"
        f"Text: {text}"
    )
    try:
        result = llm.invoke(prompt)
        code = result.content.strip().lower()[:5].split()[0]
        logger.info("LLM language detection: %s", code)
        return code
    except Exception as exc:
        logger.warning("LLM language detection failed: %s — defaulting to 'en'", exc)
        return "en"
