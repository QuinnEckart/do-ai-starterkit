import os
import hashlib
import json
from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import requests

app = Flask(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

KBAAS_BASE_URL = "https://kbaas.do-ai.run/v1"
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", 5))

_schema_initialized = False

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

def init_schema():
    """Initialize database schema for chat history."""
    global _schema_initialized
    if _schema_initialized:
        return True
    
    schema_sql = """
    CREATE TABLE IF NOT EXISTS chat_history (
        id SERIAL PRIMARY KEY,
        user_message TEXT,
        assistant_response TEXT,
        sources JSONB DEFAULT '[]'::jsonb,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute(schema_sql)
        conn.commit()
        cur.close()
        conn.close()
        _schema_initialized = True
        return True
    except Exception as e:
        app.logger.error(f"Schema init failed: {e}")
        return False

# =============================================================================
# DIGITALOCEAN KNOWLEDGE BASE API
# =============================================================================

def get_kb_uuid():
    """Get the Knowledge Base UUID from environment."""
    return os.environ.get("KB_UUID", "").strip()

def get_do_token():
    """Get the DigitalOcean API token."""
    return os.environ.get("DO_API_TOKEN", "").strip()

def retrieve_from_kb(query, top_k=RAG_TOP_K):
    """Retrieve relevant documents from DigitalOcean Knowledge Base."""
    kb_uuid = get_kb_uuid()
    token = get_do_token()
    
    if not kb_uuid or not token:
        app.logger.warning("KB_UUID or DO_API_TOKEN not configured")
        return []
    
    url = f"{KBAAS_BASE_URL}/{kb_uuid}/retrieve"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": query,
        "num_results": top_k,
        "alpha": 0.5  # Balance between semantic and keyword search
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            app.logger.error(f"KB retrieve error: {response.status_code} - {response.text[:300]}")
            return []
        
        data = response.json()
        results = data.get("results", [])
        
        formatted = []
        for r in results:
            # DO KB returns text_content and metadata.item_name
            content = r.get("text_content", r.get("content", r.get("text", "")))
            metadata = r.get("metadata", {})
            source = metadata.get("item_name", metadata.get("source", "unknown"))
            
            formatted.append({
                "content": content,
                "source": source,
                "score": r.get("score", 0)
            })
        
        return formatted
    except Exception as e:
        app.logger.error(f"KB retrieve error: {e}")
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
    init_schema()
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
    
    # Inference
    if os.environ.get("GENAI_ENDPOINT") and os.environ.get("GENAI_API_KEY"):
        status["components"]["inference"] = "configured"
    else:
        status["components"]["inference"] = "demo mode"
    
    # Knowledge Base
    kb_uuid = get_kb_uuid()
    if kb_uuid and get_do_token():
        status["components"]["knowledge_base"] = "configured"
        status["knowledge_base"] = {
            "uuid": kb_uuid[:12] + "...",
            "service": "DigitalOcean KBaaS"
        }
    else:
        status["components"]["knowledge_base"] = "not configured"
    
    return jsonify(status)

@app.route("/api/chat", methods=["POST"])
def chat():
    init_schema()
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
    
    sources = []
    context_text = ""
    
    # Retrieve from DO Knowledge Base
    if use_rag:
        contexts = retrieve_from_kb(user_message)
        if contexts:
            context_parts = []
            for i, ctx in enumerate(contexts):
                source_name = ctx.get("source", "Document")
                context_parts.append(f"[{i+1}] From '{source_name}':\n{ctx['content']}")
                sources.append({
                    "source": source_name,
                    "score": round(ctx.get("score", 0), 3)
                })
            context_text = "\n\n".join(context_parts)
    
    # Build prompt
    if context_text:
        system_prompt = f"""You are a helpful AI assistant with access to a knowledge base.
Answer questions based on the provided context. If the context doesn't contain relevant information, say so and provide a general answer.
Always cite your sources by referencing the document names when using information from the context.

Context from knowledge base:
{context_text}"""
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
    
    # Save to chat history
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
    """Test the Knowledge Base connection with detailed error reporting."""
    kb_uuid = get_kb_uuid()
    token = get_do_token()
    
    result = {
        "kb_uuid": kb_uuid if kb_uuid else "not set",
        "token_configured": bool(token),
        "token_preview": token[:20] + "..." if token else "not set"
    }
    
    if not kb_uuid or not token:
        result["status"] = "not_configured"
        result["message"] = "Set KB_UUID and DO_API_TOKEN environment variables"
        return jsonify(result)
    
    # Test retrieve with detailed error capture
    url = f"{KBAAS_BASE_URL}/{kb_uuid}/retrieve"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": "test",
        "num_results": 3,
        "alpha": 0.5
    }
    
    result["url"] = url
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result["status_code"] = response.status_code
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                result["status"] = "success"
                result["message"] = f"Retrieved {len(results)} results"
                # DO KB uses text_content
                sample = results[0].get("text_content", results[0].get("content", ""))
                result["sample"] = sample[:150] if sample else "No content"
                result["source"] = results[0].get("metadata", {}).get("item_name", "unknown")
            else:
                result["status"] = "empty"
                result["message"] = "Connected successfully but KB returned no results"
                result["raw_response"] = str(data)[:300]
        else:
            result["status"] = "error"
            result["message"] = f"API returned {response.status_code}"
            result["error_body"] = response.text[:500]
    except Exception as e:
        result["status"] = "exception"
        result["message"] = str(e)
    
    return jsonify(result)

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
