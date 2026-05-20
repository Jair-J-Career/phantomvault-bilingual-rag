import re
import logging
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

_CJK = re.compile(r"[一-鿿぀-ヿ가-퟿]")
_ARABIC = re.compile(r"[؀-ۿ]")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_LATIN_EXTENDED = re.compile(r"[áéíóúüñ¿¡àèìòùâêîôûçœæ]", re.IGNORECASE)

_ES_STOPWORDS = {"el", "la", "los", "las", "es", "en", "de", "que", "un", "una",
                 "por", "para", "con", "del", "al", "se", "su", "como", "más",
                 "pero", "cuando", "cuál", "cuáles", "qué", "cómo"}


def detect_language(text: str) -> str:
    sample = text[:500].lower()
    words = set(re.findall(r"\b\w+\b", sample))

    if _CJK.search(sample):
        return "zh"
    if _ARABIC.search(sample):
        return "ar"
    if _CYRILLIC.search(sample):
        return "ru"

    if _LATIN_EXTENDED.search(sample) or len(words & _ES_STOPWORDS) >= 2:
        return "es"

    english_indicators = {"the", "is", "are", "was", "were", "this", "that",
                          "and", "or", "but", "with", "for", "from", "have"}
    if len(words & english_indicators) >= 2:
        return "en"

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
