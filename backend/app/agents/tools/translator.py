"""
Translation tool — uses Gemini with a prompt optimised for fidelity.
Handles both single strings and lists of chunk dicts.
"""
import logging
from typing import List, Dict, Any, Union

from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

_TRANSLATION_PROMPT = """You are a professional translator. Translate the following text from {source_lang} to {target_lang}.

Rules:
- Preserve all technical terms, proper nouns, numbers, and formatting
- Translate naturally — do not transliterate
- Return ONLY the translated text, nothing else

Text to translate:
{text}"""


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translate a single string."""
    if source_lang == target_lang:
        return text

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    prompt = _TRANSLATION_PROMPT.format(
        source_lang=source_lang, target_lang=target_lang, text=text
    )
    try:
        result = llm.invoke(prompt)
        translated = result.content.strip()
        logger.info("Translated %d chars from %s to %s", len(text), source_lang, target_lang)
        return translated
    except Exception as exc:
        logger.error("Translation failed: %s", exc)
        return text  # graceful degradation — return original


def translate_chunks(
    chunks: List[Dict[str, Any]], source_lang: str, target_lang: str
) -> List[Dict[str, Any]]:
    """Translate the 'content' field of each chunk dict."""
    if source_lang == target_lang:
        return chunks

    translated = []
    for chunk in chunks:
        translated_content = translate_text(chunk["content"], source_lang, target_lang)
        translated.append({**chunk, "content": translated_content})
    return translated
