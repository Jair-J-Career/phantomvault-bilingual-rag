"""
Summarization tool.
Supports three detail levels: brief, standard, detailed.
For full-document summaries uses a map-reduce approach.
"""
import logging
from typing import List, Dict, Any, Literal

from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

DetailLevel = Literal["brief", "standard", "detailed"]

_CHUNK_SUMMARY_PROMPT = """Summarize the following text excerpt in {style}.

Text:
{text}

Summary:"""

_SYNTHESIS_PROMPT = """You have been given summaries of multiple sections of a document.
Synthesize them into a single coherent {style} summary of the whole document.

Section summaries:
{summaries}

Final summary:"""

_STYLE_MAP: Dict[str, str] = {
    "brief": "1-2 sentences",
    "standard": "one paragraph",
    "detailed": "several paragraphs covering all key points",
}


def summarize_chunks(
    chunks: List[Dict[str, Any]], detail_level: DetailLevel = "standard"
) -> str:
    """Summarize a list of retrieved chunks using map-reduce."""
    if not chunks:
        return "No content available to summarize."

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    style = _STYLE_MAP[detail_level]

    # Map: summarize each chunk
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        prompt = _CHUNK_SUMMARY_PROMPT.format(style=style, text=chunk["content"])
        try:
            result = llm.invoke(prompt)
            chunk_summaries.append(result.content.strip())
        except Exception as exc:
            logger.warning("Failed to summarize chunk %d: %s", i, exc)
            chunk_summaries.append(chunk["content"][:200])

    if len(chunk_summaries) == 1:
        return chunk_summaries[0]

    # Reduce: synthesize all chunk summaries
    synthesis_prompt = _SYNTHESIS_PROMPT.format(
        style=style, summaries="\n\n---\n\n".join(chunk_summaries)
    )
    try:
        result = llm.invoke(synthesis_prompt)
        summary = result.content.strip()
        logger.info("Synthesized %d chunk summaries (%s)", len(chunk_summaries), detail_level)
        return summary
    except Exception as exc:
        logger.error("Summary synthesis failed: %s", exc)
        return " ".join(chunk_summaries[:3])


def summarize_document(
    session_id: str, detail_level: DetailLevel = "standard"
) -> str:
    """Full-document summary via map-reduce over all stored chunks."""
    from app.services.vector_store import get_vector_store_manager
    from app.agents.tools.retriever import retrieve_chunks

    # Retrieve a broad set of chunks to cover the whole document
    chunks = retrieve_chunks(session_id, "summary overview main points", top_k=20)
    return summarize_chunks(chunks, detail_level)
