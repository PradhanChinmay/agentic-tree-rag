import firebase_admin
from firebase_admin import firestore, credentials
import time

import os
import json
from dotenv import load_dotenv

load_dotenv()

if not firebase_admin._apps:
    firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if firebase_creds_json:
        cred_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(cred_dict)
    else:
        cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def save_document_metadata(user_id: str, doc_id: str, file_name:str):
    """Saves document ownership so that the owner can see it in the sidebar."""
    db.collection('users').document(user_id).collection('documents').document(doc_id).set({
        'doc_id': doc_id,
        'filename': file_name,
        'created_at': int(time.time())
    })

def get_user_documents(user_id:str):
    docs = db.collection('users').document(user_id).collection('documents').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    return [doc.to_dict() for doc in docs]

def delete_user_document(user_id: str, doc_id: str):
    # Delete metadata
    db.collection('users').document(user_id).collection('documents').document(doc_id).delete()
    # Delete chat history
    chats = db.collection('users').document(user_id).collection('documents').document(doc_id).collection('chat').get()
    for chat in chats:
        chat.reference.delete()

def save_chat_turn(user_id: str, doc_id: str, role: str, message: str):
    db.collection('users').document(user_id).collection('documents').document(doc_id).collection('chat').add({
        'role': role,
        'message': message,
        'timestamp': int(time.time())
    })

def get_chat_history(user_id: str, doc_id: str):
    chats = db.collection('users').document(user_id).collection('documents').document(doc_id).collection('chat').order_by('timestamp').get()
    return [{"role": c.to_dict()['role'], "message": c.to_dict()['message']} for c in chats]

    
    

