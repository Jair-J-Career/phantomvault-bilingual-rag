import logging
from typing import List, Dict, Any

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
        return text  # return original on failure


def translate_chunks(
    chunks: List[Dict[str, Any]], source_lang: str, target_lang: str
) -> List[Dict[str, Any]]:
    if source_lang == target_lang:
        return chunks

    return [
        {**chunk, "content": translate_text(chunk["content"], source_lang, target_lang)}
        for chunk in chunks
    ]
