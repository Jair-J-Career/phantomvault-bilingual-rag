import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

app = FastAPI()

# Configure CORS for React connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("temp_uploads", exist_ok=True)

# Initialize Gemini 2.5 and new Embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

vector_store = None

@app.get("/")
def read_root():
    return {"status": "PhantomVault API is Online (Bilingual Mode)"}

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