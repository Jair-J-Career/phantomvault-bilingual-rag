import os
from fastapi import FastAPI, UploadFile, File
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate

# NEW: Import the Google Gemini modules
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

app = FastAPI()
os.makedirs("temp_uploads", exist_ok=True)

# NEW: Initialize Gemini instead of OpenAI
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

vector_store = None

@app.get("/")
def read_root():
    return {"status": "PhantomVault API is Online (Powered by Gemini)"}

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    global vector_store
    file_path = f"temp_uploads/{file.filename}"
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    
    # This will now use Gemini to create the mathematical vectors
    vector_store = Chroma.from_documents(documents=chunks, embedding=embeddings)
    
    return {"status": "File processed and memorized!", "chunks": len(chunks)}

@app.post("/api/ask")
async def ask_question(question: str):
    if not vector_store:
        return {"error": "Please upload a PDF first."}

    system_prompt = (
        "You are an expert bilingual assistant. "
        "Use the following pieces of retrieved context to answer the user's question. "
        "CRITICAL INSTRUCTION: You must detect the language of the user's question and "
        "reply EXCLUSIVELY in that same language. If the context is in English but the "
        "question is in Spanish, translate the facts and answer natively in Spanish.\n\n"
        "Context: {context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
    retriever = vector_store.as_retriever()
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    
    response = rag_chain.invoke({"input": question})
    
    return {"question": question, "answer": response["answer"]}