# Vectorless RAG Engine

A next-generation Retrieval-Augmented Generation (RAG) system that ditches traditional vector embeddings in favor of LLM-generated structural hierarchy (JSON Trees) to achieve highly accurate, context-aware document querying.

## 🏗️ Project Architecture

This project is split into a robust Python/FastAPI backend and a sleek React/Vite frontend. It uses Firebase for authentication and metadata, Redis for high-speed document state storage, and Google's Gemini for all LLM processing.

### The Core Workflow:

1. **Upload & Parse**: A user uploads a document (PDF, DOCX, XLSX). The FastAPI backend breaks the document down into structural chunks (nodes).
2. **Tree Generation**: The backend passes these chunks to Gemini to generate a highly detailed, hierarchical **JSON Tree Index**. This index contains summaries and metadata for every section without the raw text.
3. **Storage**: The raw chunks and the JSON Tree Index are stored in **RedisJSON** for blazingly fast access.
4. **Scatter (Routing)**: When a user asks a question, the backend sends the *entire JSON Tree Index* to Gemini. Gemini analyzes the document structure and returns the exact `node_ids` that contain the answer.
5. **Gather (Synthesis)**: The backend fetches only those specific `node_ids` (the raw text) from Redis and passes them to Gemini to synthesize the final, highly accurate answer.
6. **Streaming Chat**: The answer is streamed back to the React frontend via WebSockets in real-time, accompanied by the exact sources used.

---

## 🤔 Why Vectorless RAG?

### Vectorless RAG vs. Traditional Vectored RAG

Traditional RAG relies on converting text into number arrays (vectors) and using mathematical similarity (Cosine Distance) to find relevant text. While fast, this has massive flaws:

- **Loss of Context**: Vectors chop documents into arbitrary chunks. If you chunk a document, paragraph 2 might lose the context of paragraph 1.
- **Semantic Blindness**: Vector searches find text that *sounds similar* to the query, not necessarily text that *answers* the query. If you ask "What are the disadvantages?", a vector database might return a paragraph about "advantages" because the words are semantically close.
- **The Vectorless Advantage**: Instead of math, Vectorless RAG uses an LLM's reasoning to look at a logical map (JSON Tree) of your entire document. It understands chapters, sections, and the *flow* of information, allowing it to accurately pinpoint the right data just like a human reading a table of contents.

### Vectorless RAG vs. Directly Uploading to a GPT

Why not just upload a 500-page PDF to ChatGPT or Gemini and ask questions?

- **Context Windows & Cost**: Passing massive documents into an LLM for *every single question* consumes enormous amounts of tokens. It is incredibly expensive and hits rate limits almost instantly.
- **Speed**: Processing a 1-million token document takes time. A Vectorless RAG system only passes the tiny fraction of the document that actually matters, resulting in instant answers.
- **Hallucination Control**: When you shove massive amounts of data into an LLM, it can get "lost in the middle" and start hallucinating. By fetching only the exact, relevant raw text nodes from Redis, we ground the LLM strictly to the facts, drastically reducing hallucinations.

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: React.js with Vite
- **Styling**: Vanilla CSS (Glassmorphism & Modern UI)
- **Auth**: Firebase Authentication (Google OAuth)

### Backend
- **Framework**: FastAPI (Python)
- **LLM Engine**: Google Gemini (2.5 Flash / Pro)
- **State/Caching**: Redis (RedisJSON)
- **Database**: Firebase Firestore (Metadata & Chat History)

## 🚀 Getting Started

Ensure you have your `.env` and `.env.local` files configured properly for both the backend and frontend.

**Start the Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Start the Frontend:**
```bash
cd frontend/frontend
npm install
npm run dev
```
