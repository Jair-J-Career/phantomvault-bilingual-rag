from functools import lru_cache
from langchain_google_genai import GoogleGenerativeAIEmbeddings


@lru_cache(maxsize=1)
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
