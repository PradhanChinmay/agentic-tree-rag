import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure the SDK
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# We'll use Gemini Flash Latest to avoid strict 20 req/day rate limits on 2.5 flash
# Flash is usually perfect for structuring and extracting data fast.
model = genai.GenerativeModel('gemini-flash-latest')

async def generate_json_tree(parsed_data: dict) -> str:
    """
    Reads the parsed nodes and generates the heirarchial structural index.
    """
    # We define the strict schema instructions that we want gemini to follow
    schema_instruction = """
    You are a data structuring agent. Analyze the provided parsed document nodes.
    Your job is to group these nodes into logical sections and summerize them.

    You MUST respond with a valid JSON object matching this exact structure:
    {
      "document_title": "Infer a title",
      "overall_summary": "A 2-3 sentence summary of the entire document",
      "sections": [
        {
          "section_title": "Name of the section/chapter",
          "section_summary": "What this specific section covers",
          "node_ids": ["page_1", "page_2"] // ONLY use node_ids that exist in the input data
        }
      ]
    }
    DO NOT include the raw text in your output, only the node_ids.
    """
    prompt = f"{schema_instruction}\n\nInput Data:\n{json.dumps(parsed_data)}"
    
    # Force gemini to output only json
    response = await model.generate_content_async(
        prompt,
        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json",
        ),
    )

    # Parse the string response back into a Python dictionary
    try:
        tree_index = json.loads(response.text)
        return tree_index
    except json.JSONDecodeError as e:
        raise Exception("Gemini failed to return valid JSON.")


async def route_query(query: str, tree_index: dict) -> list:
    """
    STEP 1 (Scatter): Asks Gemini to look at the tree index and decide 
    which node_ids hold the answer to the user's query.
    """
    routing_instruction = """
    You are a document routing agent. Look at the user's query and the provided Document Index.
    Determine which sections of the document are most likely to contain the answer.
    
    You MUST output a valid JSON object matching this exact schema:
    {
        "target_nodes": ["node_id_1", "node_id_2"]
    }
    Only include node_ids that explicitly exist in the Document Index. 
    If the answer is not in the index, return an empty list.
    """

    prompt = f"{routing_instruction}\n\nUser Query: {query}\n\nDocument Index:\n{json.dumps(tree_index)}"
    
    response = await model.generate_content_async(
        prompt,
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1 # Low temperature for deterministic routing
        ),
    )
    
    try:
        routing_decision = json.loads(response.text)
        return routing_decision.get("target_nodes", [])
    except json.JSONDecodeError:
        fixed_json = await repair_json(response.text)
        return fixed_json.get("target_nodes", [])

async def synthesize_answer(query: str, context: str) -> str:
    """
    STEP 2 (Gather): Takes the raw text fetched from Redis and generates the final answer.
    """

    if not context:
        return "I could not find relevant information in the document to answer this question."

    synthesis_instruction = """
    You are a helpful and highly accurate assistant. Answer the user's question 
    using ONLY the provided Context from the document. 
    
    If the context contains multiple contradicting points, mention them. 
    If the answer cannot be fully determined from the context, say so.
    Do not use outside knowledge.
    """
    prompt = f"{synthesis_instruction}\n\nContext:\n{context}\n\nUser Query: {query}"

    response = await model.generate_content_async(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4 # Slightly higher for natural language generation
        )
    )
    
    return response.text

async def parse_image_with_vision(file_bytes: bytes, mime_type: str)-> dict:
    """Vision Capability: Converts an image to a descriptive text node."""
    prompt = "Describe this image in extreme detail. Include all text, charts, and data points."
    vision_part = {"mime_type": mime_type, "data": file_bytes}

    response = await model.generate_content_async([prompt, vision_part])
    return {
        "node_type": "image",
        "node_id": "image_1",
        "content": response.text
    }

async def synthesize_answer_stream(query: str, context: str, chat_history: list):
    """Yields chunks of the answer for WebSockets + Multi-turn Context."""
    # Format history for Gemini
    formatted_history = []

    for chat in chat_history:
        role = "user" if chat['role'] == "user" else "model"
        formatted_history.append({"role": role, "parts": [chat['message']]})
    
    chat_session = model.start_chat(history=formatted_history)

    synthesis_instruction = f"""
    Answer the user using ONLY this Context:
    {context}
    """

    response = await chat_session.send_message_async(
        f"{synthesis_instruction}\n\nUser: {query}", 
        stream=True
    )
    
    try:
        async for chunk in response:
            yield chunk.text
    except StopAsyncIteration:
        # Gemini sometimes leaks StopAsyncIteration if the response is completely empty
        pass
    except ValueError as e:
        # Sometimes if the response is blocked or empty, chunk.text raises ValueError
        print(f"Gemini yielded an empty or blocked chunk: {e}")
        yield "I'm sorry, I couldn't generate a response for that. It might have been blocked or empty."

async def repair_json(bad_json_string: str) -> dict:
    """Edge Case Handler: Asks Gemini to fix malformed JSON."""
    prompt = f"Fix this malformed JSON string and return ONLY valid JSON:\n{bad_json_string}"
    response = await model.generate_content_async(
        prompt,
        generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)

