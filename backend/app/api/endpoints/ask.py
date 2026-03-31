import logging

from fastapi import APIRouter, HTTPException, Request
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.limiter import limiter
from app.models.schemas import AskRequest, AskResponse, ErrorResponse
from app.services.vector_store import get_vector_store_manager

router = APIRouter()
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert bilingual assistant. "
    "Use the following pieces of retrieved context to answer the user's question. "
    "CRITICAL INSTRUCTION: You must detect the language of the user's question and "
    "reply EXCLUSIVELY in that same language. If the context is in English but the "
    "question is in Spanish, translate the facts and answer natively in Spanish.\n\n"
    "Context: {context}"
)


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)


@router.post(
    "/ask",
    response_model=AskResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
@limiter.limit("20/minute")
async def ask_question(request: Request, body: AskRequest):
    manager = get_vector_store_manager()

    if not manager.session_exists(body.session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please upload a document first.",
        )

    try:
        retriever = manager.get_retriever(body.session_id)
        prompt = ChatPromptTemplate.from_messages(
            [("system", _SYSTEM_PROMPT), ("human", "{input}")]
        )
        qa_chain = create_stuff_documents_chain(_get_llm(), prompt)
        rag_chain = create_retrieval_chain(retriever, qa_chain)

        response = rag_chain.invoke({"input": body.question})
    except Exception as exc:
        logger.error("RAG chain error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate an answer.")

    return AskResponse(
        question=body.question,
        answer=response["answer"],
        session_id=body.session_id,
    )
