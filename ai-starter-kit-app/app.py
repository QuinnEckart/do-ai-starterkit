import os
import hashlib
import json
from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import boto3
from botocore.client import Config
import requests

app = Flask(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

RAG_TOP_K = int(os.environ.get("RAG_TOP_K", 5))
RAG_ALPHA = float(os.environ.get("RAG_ALPHA", 0.5))

# =============================================================================
# CONNECTION HELPERS
# =============================================================================

def get_pg_connection():
    return psycopg2.connect(
        host=os.environ.get("PG_HOST"),
        port=os.environ.get("PG_PORT", 25060),
        database=os.environ.get("PG_DATABASE", "kb"),
        user=os.environ.get("PG_USER"),
        password=os.environ.get("PG_PASSWORD"),
        sslmode="require"
    )

def get_valkey_client():
    return redis.Redis(
        host=os.environ.get("VALKEY_HOST"),
        port=int(os.environ.get("VALKEY_PORT", 25061)),
        password=os.environ.get("VALKEY_PASSWORD"),
        ssl=True
    )

def init_db():
    """Initialize chat history table."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                user_message TEXT,
                assistant_response TEXT,
                sources JSONB DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        app.logger.error(f"DB init failed: {e}")
        return False

# =============================================================================
# DIGITALOCEAN KNOWLEDGE BASE API
# =============================================================================

def retrieve_from_do_kb(query, top_k=RAG_TOP_K, alpha=RAG_ALPHA):
    """
    Retrieve relevant chunks from DigitalOcean Knowledge Base API.
    https://kbaas.do-ai.run/v1/<kb-uuid>/retrieve
    """
    kb_uuid = os.environ.get("KB_UUID", "")
    do_token = os.environ.get("DO_API_TOKEN", "")
    
    if not kb_uuid or not do_token:
        app.logger.warning("KB_UUID or DO_API_TOKEN not configured")
        return []
    
    url = f"https://kbaas.do-ai.run/v1/{kb_uuid}/retrieve"
    headers = {
        "Authorization": f"Bearer {do_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": query,
        "num_results": top_k,
        "alpha": alpha
    }
    
    try:
        app.logger.info(f"Querying DO KB: {kb_uuid}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            app.logger.error(f"DO KB API error: {response.status_code} - {response.text[:200]}")
            return []
        
        data = response.json()
        results = data.get("results", [])
        
        formatted = []
        for r in results:
            formatted.append({
                "content": r.get("text_content", ""),
                "source": r.get("metadata", {}).get("item_name", "Unknown"),
                "metadata": r.get("metadata", {})
            })
        
        app.logger.info(f"Retrieved {len(formatted)} chunks from DO KB")
        return formatted
        
    except Exception as e:
        app.logger.error(f"DO KB retrieve error: {e}")
        return []

# =============================================================================
# INFERENCE
# =============================================================================

def call_inference(messages):
    """Call GenAI endpoint for chat completion."""
    endpoint = os.environ.get("GENAI_ENDPOINT", "")
    api_key = os.environ.get("GENAI_API_KEY", "")
    model = os.environ.get("DEFAULT_MODEL", "")
    
    if not endpoint or not api_key:
        user_message = messages[-1].get("content", "") if messages else ""
        return f"[Demo Mode] You said: {user_message}\n\nTo enable AI, set GENAI_ENDPOINT and GENAI_API_KEY."
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {"messages": messages, "max_tokens": 1024, "temperature": 0.7}
    if model:
        payload["model"] = model
    
    base_url = endpoint.rstrip('/')
    paths_to_try = ["/api/v1/chat/completions", "/v1/chat/completions", "/chat/completions", ""]
    
    for path in paths_to_try:
        try:
            url = f"{base_url}{path}"
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 404:
                continue
            if response.status_code != 200:
                return f"API error ({response.status_code}): {response.text[:300]}"
            
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0].get("message", {}).get("content", "No content")
            elif "response" in data:
                return data["response"]
            elif "output" in data:
                return data["output"]
            else:
                return f"Unexpected response: {str(data)[:300]}"
        except requests.exceptions.Timeout:
            return "Request timed out. Please try again."
        except Exception:
            continue
    
    return "Could not connect to GenAI endpoint."

def get_cache_key(message, use_rag):
    return f"chat:{hashlib.md5((message + str(use_rag)).encode()).hexdigest()}"

# =============================================================================
# ROUTES
# =============================================================================

@app.route("/")
def index():
    init_db()
    return render_template("index.html")

@app.route("/health")
def health():
    status = {"status": "healthy", "components": {}}
    
    # PostgreSQL
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        status["components"]["postgres"] = "connected"
    except Exception as e:
        status["components"]["postgres"] = f"error: {str(e)[:100]}"
        status["status"] = "degraded"
    
    # Valkey
    try:
        vk = get_valkey_client()
        vk.ping()
        status["components"]["valkey"] = "connected"
    except Exception as e:
        status["components"]["valkey"] = f"error: {str(e)[:100]}"
        status["status"] = "degraded"
    
    # GenAI Inference
    if os.environ.get("GENAI_ENDPOINT") and os.environ.get("GENAI_API_KEY"):
        status["components"]["inference"] = "configured"
    else:
        status["components"]["inference"] = "demo mode"
    
    # DO Knowledge Base
    kb_uuid = os.environ.get("KB_UUID", "")
    if kb_uuid:
        status["components"]["knowledge_base"] = "configured"
        status["knowledge_base"] = {"uuid": kb_uuid[:8] + "..."}
    else:
        status["components"]["knowledge_base"] = "not configured"
        status["knowledge_base"] = {"uuid": None}
    
    return jsonify(status)

@app.route("/api/chat", methods=["POST"])
def chat():
    init_db()
    data = request.get_json()
    user_message = data.get("message", "").strip()
    use_rag = data.get("use_rag", True)
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    cache_key = get_cache_key(user_message, use_rag)
    
    # Check cache
    try:
        vk = get_valkey_client()
        cached = vk.get(cache_key)
        if cached:
            cached_data = json.loads(cached.decode("utf-8"))
            return jsonify({**cached_data, "cached": True})
    except Exception:
        pass
    
    # Retrieve context from DO Knowledge Base
    sources = []
    context_text = ""
    
    if use_rag:
        chunks = retrieve_from_do_kb(user_message)
        if chunks:
            context_parts = []
            for i, chunk in enumerate(chunks):
                source_name = chunk.get("source", "Unknown")
                content = chunk.get("content", "")
                context_parts.append(f"[{i+1}] From '{source_name}':\n{content}")
                sources.append({
                    "source": source_name,
                    "preview": content[:100] + "..." if len(content) > 100 else content
                })
            context_text = "\n\n".join(context_parts)
    
    # Build prompt
    if context_text:
        system_prompt = """You are a helpful AI assistant with access to a knowledge base.
Answer questions based on the provided context. If the context doesn't contain relevant information, say so and provide a general answer.
Always cite your sources by referencing the document names when using information from the context.

Context from knowledge base:
{context}""".format(context=context_text)
    else:
        system_prompt = "You are a helpful AI assistant. Be concise and helpful."
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    response_text = call_inference(messages)
    
    result = {"response": response_text, "sources": sources, "cached": False}
    
    # Cache response
    try:
        vk = get_valkey_client()
        cache_ttl = int(os.environ.get("CACHE_TTL_SECONDS", 3600))
        vk.setex(cache_key, cache_ttl, json.dumps({"response": response_text, "sources": sources}))
    except Exception:
        pass
    
    # Save to history
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_history (user_message, assistant_response, sources) VALUES (%s, %s, %s)",
            (user_message, response_text, json.dumps(sources))
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass
    
    return jsonify(result)

@app.route("/api/test-kb", methods=["POST"])
def test_kb():
    """Test the DO Knowledge Base connection."""
    kb_uuid = os.environ.get("KB_UUID", "")
    do_token = os.environ.get("DO_API_TOKEN", "")
    
    result = {
        "kb_uuid": kb_uuid[:8] + "..." if kb_uuid else None,
        "token_configured": bool(do_token)
    }
    
    if not kb_uuid or not do_token:
        result["status"] = "not_configured"
        result["error"] = "KB_UUID or DO_API_TOKEN not set"
        return jsonify(result)
    
    # Test with a simple query
    chunks = retrieve_from_do_kb("test query", top_k=1)
    
    if chunks:
        result["status"] = "success"
        result["sample_result"] = chunks[0].get("source", "Unknown")
    else:
        result["status"] = "no_results"
        result["message"] = "KB connected but no results returned. This could be normal if KB is empty."
    
    return jsonify(result)

@app.route("/api/history", methods=["GET"])
def history():
    try:
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT user_message, assistant_response, sources, created_at 
            FROM chat_history 
            ORDER BY created_at DESC 
            LIMIT 50
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        history_list = []
        for row in rows:
            history_list.append({
                "user_message": row["user_message"],
                "assistant_response": row["assistant_response"],
                "sources": row.get("sources", []),
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })
        return jsonify({"history": history_list})
    except Exception as e:
        return jsonify({"error": str(e), "history": []})

@app.route("/api/clear-cache", methods=["POST"])
def clear_cache():
    try:
        vk = get_valkey_client()
        keys = vk.keys("chat:*")
        if keys:
            vk.delete(*keys)
        return jsonify({"status": "ok", "cleared": len(keys)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
