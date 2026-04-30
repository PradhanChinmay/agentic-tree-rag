import redis
import json
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def save_document_state(doc_id: str, parsed_data: dict, tree_index: dict = None):
    """
    Stores both the raw parsed nodes and the Gemini tree index in RedisJSON.
    """
    #create the master json object
    doc_state = {
        "doc_id": doc_id,
        "parsed_data": parsed_data,
        "tree_index": tree_index
    }
    
    # Store in Redis at root path '$'
    # The key will look like "document:12345"
    redis_client.json().set(f"document:{doc_id}", "$", doc_state)

def get_document_tree(doc_id: str):
    """Fetches just the tree index from Redis"""
    return redis_client.json().get(f"document:{doc_id}", "$.tree_index")

def get_specific_nodes(doc_id: str, requested_node_ids: list) -> str:
    """
    Fetches the raw text for specific node IDs from the Redis document state.
    """
    # Fetch the parsed structure array from Redis
    # RedisJSON returns a list containing the target data, hence the [0]
    raw_nodes_data = redis_client.json().get(f"document:{doc_id}", "$.parsed_data.structure")
    
    if not raw_nodes_data or not raw_nodes_data[0]:
        return ""

    raw_nodes = raw_nodes_data[0]
    
    # Filter only the nodes the LLM asked for
    gathered_context = []
    for node in raw_nodes:
        if node.get("node_id") in requested_node_ids:
            gathered_context.append(f"--- [Source: {node['node_id']}] ---\n{node['content']}")
            
    return "\n\n".join(gathered_context)

def delete_document_state(doc_id: str):
    """Deletes the document state from Redis."""
    redis_client.delete(f"document:{doc_id}")
