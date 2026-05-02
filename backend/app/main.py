import uuid
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, WebSocketDisconnect, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import json

from app.auth import verify_token, auth
from app.services.document_parser import parse_pdf, parse_docx, parse_excel
from app.services.gemini_service import generate_json_tree, route_query, synthesize_answer, synthesize_answer_stream
from app.services.redis_service import save_document_state, get_document_tree, get_specific_nodes, delete_document_state
from app.services.firestore_service import save_document_metadata, get_user_documents, delete_user_document, save_chat_turn, get_chat_history

app = FastAPI(title = "Vectorless RAG Engine")

import os
from dotenv import load_dotenv

load_dotenv()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload")
async def upload_and_index_document(file: UploadFile=File(...), user: dict = Depends(verify_token)):
    try:
        #Read file
        file_bytes = await file.read()
        file_ext = file.filename.split('.')[-1].lower()

        # Phase 1: Structural Parsing
        if file_ext == "pdf":
            parsed_structure = parse_pdf(file_bytes)
        elif file_ext in ['docx', 'doc']:
            parsed_structure = parse_docx(file_bytes)
        elif file_ext in ['xlsx', 'xls']:
            parsed_structure = parse_excel(file_bytes)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        #Phase 2: Generate tree index via gemini
        tree_index = await generate_json_tree(parsed_structure)

        # Save everything into redis
        doc_id = str(uuid.uuid4())
        save_document_state(doc_id=doc_id, parsed_data=parsed_structure, tree_index=tree_index)
        save_document_metadata(user.get("uid"), doc_id, file.filename)

        return {
            "message": "Document indexed successfully",
            "doc_id": doc_id,
            "tree_preview": tree_index
        }
    
    except Exception as e:
        import traceback
        with open("error_log.txt", "w") as f:
            f.write(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Pydantic model for the chat request body
class ChatRequest(BaseModel):
    doc_id: str
    query: str

@app.post("/api/chat")
async def chat_with_document(request: ChatRequest, user: dict = Depends(verify_token)):
    try:
        #fetch the tree index from the redis
        tree_index_data = get_document_tree(request.doc_id)

        if not tree_index_data or not tree_index_data[0]:
            raise HTTPException(status_code=404, detail="Document index not found")

        tree_index = tree_index_data[0]

        # 2. Scatter: Ask Gemini which nodes to check
        target_nodes = await route_query(request.query, tree_index)

        if not target_nodes:
            return {
                "answer": "I couldn't find any relevant sections in the document index to answer that.",
                "sources_used": []
            }
        
        # 3. Fetch specific raw text blocks from Redis
        gathered_context = get_specific_nodes(request.doc_id, target_nodes)

        # 4. Gather: Generate final answer
        final_answer = await synthesize_answer(request.query, gathered_context)

        return {
            "answer": final_answer,
            "sources_used": target_nodes # Great for UI transparency!
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ROUTES FOR SIDEBAR HISTORY ---
@app.get("/api/documents")
async def list_documents(user: dict = Depends(verify_token)):
    return get_user_documents(user.get("uid"))

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(verify_token)):
    # Delete from Firestore
    delete_user_document(user.get("uid"), doc_id)
    # Delete from Redis
    delete_document_state(doc_id)
    return {"status": "deleted"}

@app.get("/api/chat/{doc_id}/history")
async def fetch_chat_history(doc_id: str, user: dict = Depends(verify_token)):
    return get_chat_history(user.get("uid"), doc_id)

# --- WEBSOCKET ROUTE FOR STREAMING CHAT ---

@app.websocket("/ws/chat/{doc_id}")
async def websocket_chat(websocket: WebSocket, doc_id: str, token: str):
    await websocket.accept()
    
    try:
        # Verify Firebase token manually since Depends() doesn't work well in WebSockets
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token.get("uid")
    except Exception:
        await websocket.close(code=1008)
        return

    try:
        while True:
            try:
                # Wait for user message
                data = await websocket.receive_text()
                payload = json.loads(data)
                user_query = payload.get("query")

                # Fetch history BEFORE saving the current turn to avoid duplicate user turns in Gemini history
                history = get_chat_history(user_id, doc_id)

                # Save user turn to Firestore
                save_chat_turn(user_id, doc_id, "user", user_query)
                
                # Fetch tree, and route
                tree_index_data = get_document_tree(doc_id)
                target_nodes = await route_query(user_query, tree_index_data[0])
                gathered_context = get_specific_nodes(doc_id, target_nodes)

                # Send a "start" signal so UI knows streaming is beginning
                await websocket.send_json({"type": "start", "sources": target_nodes})

                full_answer = ""
                # Stream the answer chunks
                async for chunk in synthesize_answer_stream(user_query, gathered_context, history):
                    full_answer += chunk
                    await websocket.send_json({"type": "chunk", "text": chunk})
                
                # Save AI turn to Firestore
                save_chat_turn(user_id, doc_id, "ai", full_answer)
                
                # Send end signal
                await websocket.send_json({"type": "end"})
            except Exception as inner_e:
                import traceback
                with open("ws_error_log.txt", "w") as f:
                    f.write("ERROR IN WEBSOCKET LOOP:\n")
                    f.write(traceback.format_exc())
                
                # Ensure the UI transitions from 'waiting' to 'streaming' so it can display the error
                await websocket.send_json({"type": "start", "sources": []})
                
                # Determine user-friendly error message
                error_msg = f"An error occurred: {str(inner_e)}"
                if "429" in str(inner_e) or "ResourceExhausted" in str(inner_e) or "Quota" in str(inner_e):
                    error_msg = "⚠️ The Gemini API rate limit has been exceeded (Free Tier allows 5 requests). Please wait a few moments and try again."
                
                # Send the error text as a chunk so the user sees it
                await websocket.send_json({"type": "chunk", "text": error_msg})
                
                # End the stream
                await websocket.send_json({"type": "end"})
                break

    except WebSocketDisconnect:
        print("Client disconnected")

