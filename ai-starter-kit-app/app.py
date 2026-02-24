import os
import hashlib
import json
import re
from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import boto3
from botocore.client import Config
import requests

app = Flask(__name__)

# =============================================================================
# CONFIGURATION (all from environment, with sensible defaults)
# =============================================================================

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 512))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 64))
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", 5))
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", 1024))

# =============================================================================
# DATABASE SCHEMA (auto-created on first request)
# =============================================================================

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    content TEXT,
    file_type TEXT,
    metadata JSONB DEFAULT '{{}}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector({dimensions}),
    chunk_index INTEGER,
    metadata JSONB DEFAULT '{{}}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_message TEXT,
    assistant_response TEXT,
    sources JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'chunks_embedding_idx') THEN
        CREATE INDEX chunks_embedding_idx ON chunks 
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    END IF;
END $$;
""".format(dimensions=EMBEDDING_DIMENSIONS)

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

def get_spaces_client():
    session = boto3.session.Session()
    return session.client(
        "s3",
        region_name=os.environ.get("SPACES_REGION", "nyc3"),
        endpoint_url=f"https://{os.environ.get('SPACES_REGION', 'nyc3')}.digitaloceanspaces.com",
        aws_access_key_id=os.environ.get("SPACES_ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("SPACES_SECRET_KEY"),
        config=Config(signature_version="s3v4")
    )

def init_schema():
    global _schema_initialized
    if _schema_initialized:
        return True
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute(SCHEMA_SQL)
        conn.commit()
        cur.close()
        conn.close()
        _schema_initialized = True
        return True
    except Exception as e:
        app.logger.error(f"Schema init failed: {e}")
        return False

# =============================================================================
# EMBEDDING HELPERS
# =============================================================================

def get_embedding(text):
    """Generate embedding for text using configured endpoint."""
    endpoint = os.environ.get("EMBEDDING_ENDPOINT") or os.environ.get("GENAI_ENDPOINT", "")
    api_key = os.environ.get("EMBEDDING_API_KEY") or os.environ.get("GENAI_API_KEY", "")
    model = os.environ.get("EMBEDDING_MODEL", "bge-large-en-v1.5")
    
    if not endpoint or not api_key:
        app.logger.warning("Embedding not configured: missing endpoint or API key")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    base_url = endpoint.rstrip('/')
    paths_to_try = ["/v1/embeddings", "/api/v1/embeddings", "/embeddings", ""]
    last_error = None
    
    for path in paths_to_try:
        try:
            url = f"{base_url}{path}"
            app.logger.info(f"Trying embedding endpoint: {url}")
            response = requests.post(
                url,
                headers=headers,
                json={"input": text, "model": model},
                timeout=30
            )
            
            if response.status_code == 404:
                last_error = f"404 at {url}"
                continue
            
            if response.status_code != 200:
                last_error = f"{response.status_code}: {response.text[:200]}"
                app.logger.error(f"Embedding API error at {url}: {last_error}")
                continue
                
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                app.logger.info(f"Embedding successful via {url}")
                return data["data"][0].get("embedding")
            elif "embedding" in data:
                app.logger.info(f"Embedding successful via {url}")
                return data["embedding"]
            else:
                last_error = f"Unexpected response format: {str(data)[:100]}"
                app.logger.error(f"Embedding response format error: {last_error}")
        except Exception as e:
            last_error = str(e)
            app.logger.error(f"Embedding exception at {url}: {e}")
            continue
    
    app.logger.error(f"All embedding endpoints failed. Last error: {last_error}")
    return None

# =============================================================================
# CHUNKING HELPERS
# =============================================================================

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks, respecting sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence.split())
        
        if current_length + sentence_length > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            overlap_words = []
            overlap_length = 0
            for s in reversed(current_chunk):
                s_len = len(s.split())
                if overlap_length + s_len <= overlap:
                    overlap_words.insert(0, s)
                    overlap_length += s_len
                else:
                    break
            current_chunk = overlap_words
            current_length = overlap_length
        
        current_chunk.append(sentence)
        current_length += sentence_length
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

# =============================================================================
# RAG RETRIEVAL
# =============================================================================

def retrieve_context(query, top_k=RAG_TOP_K):
    """Retrieve relevant chunks for a query using vector similarity."""
    query_embedding = get_embedding(query)
    
    if not query_embedding:
        return []
    
    try:
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        cur.execute("""
            SELECT c.content, c.chunk_index, d.filename, d.id as document_id,
                   1 - (c.embedding <=> %s::vector) as similarity
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """, (embedding_str, embedding_str, top_k))
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return [dict(r) for r in results]
    except Exception as e:
        app.logger.error(f"Retrieval error: {e}")
        return []

# =============================================================================
# INFERENCE
# =============================================================================

def call_inference(messages):
    """Call inference endpoint with optional RAG context."""
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
        except Exception as e:
            continue
    
    return "Could not connect to GenAI endpoint."

def get_cache_key(message):
    return f"chat:{hashlib.md5(message.encode()).hexdigest()}"

# =============================================================================
# ROUTES: CORE
# =============================================================================

@app.route("/")
def index():
    init_schema()
    return render_template("index.html")

@app.route("/health")
def health():
    status = {"status": "healthy", "components": {}}
    
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
    
    try:
        cur = get_pg_connection().cursor()
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        if cur.fetchone():
            status["components"]["pgvector"] = "enabled"
        else:
            status["components"]["pgvector"] = "not enabled"
        cur.close()
    except Exception:
        status["components"]["pgvector"] = "unknown"
    
    try:
        vk = get_valkey_client()
        vk.ping()
        status["components"]["valkey"] = "connected"
    except Exception as e:
        status["components"]["valkey"] = f"error: {str(e)[:100]}"
        status["status"] = "degraded"
    
    try:
        s3 = get_spaces_client()
        bucket = os.environ.get("SPACES_BUCKET")
        if bucket:
            s3.head_bucket(Bucket=bucket)
            status["components"]["spaces"] = "connected"
        else:
            status["components"]["spaces"] = "not configured"
    except Exception as e:
        status["components"]["spaces"] = f"error: {str(e)[:100]}"
        status["status"] = "degraded"
    
    if os.environ.get("GENAI_ENDPOINT") and os.environ.get("GENAI_API_KEY"):
        status["components"]["inference"] = "configured"
    else:
        status["components"]["inference"] = "demo mode"
    
    if os.environ.get("EMBEDDING_ENDPOINT") or os.environ.get("GENAI_ENDPOINT"):
        status["components"]["embeddings"] = "configured"
    else:
        status["components"]["embeddings"] = "not configured"
    
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM documents")
        doc_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL")
        embedded_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        status["knowledge_base"] = {
            "documents": doc_count, 
            "chunks": chunk_count,
            "chunks_with_embeddings": embedded_count,
            "rag_ready": embedded_count > 0
        }
    except Exception:
        status["knowledge_base"] = {"documents": 0, "chunks": 0, "chunks_with_embeddings": 0, "rag_ready": False}
    
    return jsonify(status)


@app.route("/api/test-embedding", methods=["POST"])
def test_embedding():
    """Test if the embedding endpoint is working."""
    data = request.get_json() or {}
    test_text = data.get("text", "This is a test sentence for embedding.")
    
    endpoint = os.environ.get("EMBEDDING_ENDPOINT") or os.environ.get("GENAI_ENDPOINT", "")
    model = os.environ.get("EMBEDDING_MODEL", "bge-large-en-v1.5")
    
    result = {
        "endpoint": endpoint[:50] + "..." if len(endpoint) > 50 else endpoint,
        "model": model,
        "test_text": test_text[:50] + "..." if len(test_text) > 50 else test_text,
    }
    
    embedding = get_embedding(test_text)
    
    if embedding:
        result["status"] = "success"
        result["embedding_dimensions"] = len(embedding)
        result["sample"] = embedding[:5]
    else:
        result["status"] = "failed"
        result["error"] = "Could not generate embedding. Check logs for details."
    
    return jsonify(result)

# =============================================================================
# ROUTES: RAG CHAT
# =============================================================================

@app.route("/api/chat", methods=["POST"])
def chat():
    init_schema()
    data = request.get_json()
    user_message = data.get("message", "").strip()
    use_rag = data.get("use_rag", True)
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    cache_key = get_cache_key(user_message + str(use_rag))
    
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
    
    if use_rag:
        contexts = retrieve_context(user_message)
        if contexts:
            context_parts = []
            for i, ctx in enumerate(contexts):
                context_parts.append(f"[{i+1}] From '{ctx['filename']}':\n{ctx['content']}")
                sources.append({
                    "filename": ctx["filename"],
                    "chunk_index": ctx["chunk_index"],
                    "similarity": round(ctx["similarity"], 3) if ctx.get("similarity") else None
                })
            context_text = "\n\n".join(context_parts)
    
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
    
    try:
        vk = get_valkey_client()
        cache_ttl = int(os.environ.get("CACHE_TTL_SECONDS", 3600))
        vk.setex(cache_key, cache_ttl, json.dumps({"response": response_text, "sources": sources}))
    except Exception:
        pass
    
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

# =============================================================================
# ROUTES: DOCUMENT MANAGEMENT
# =============================================================================

@app.route("/api/documents", methods=["GET"])
def list_documents():
    init_schema()
    try:
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT d.id, d.filename, d.file_type, d.created_at,
                   COUNT(c.id) as chunk_count
            FROM documents d
            LEFT JOIN chunks c ON d.id = c.document_id
            GROUP BY d.id
            ORDER BY d.created_at DESC
        """)
        docs = [dict(r) for r in cur.fetchall()]
        for doc in docs:
            if doc.get("created_at"):
                doc["created_at"] = doc["created_at"].isoformat()
        cur.close()
        conn.close()
        return jsonify({"documents": docs})
    except Exception as e:
        return jsonify({"error": str(e), "documents": []})

@app.route("/api/documents", methods=["POST"])
def upload_document():
    init_schema()
    
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No filename"}), 400
    
    filename = file.filename
    content = file.read().decode("utf-8", errors="ignore")
    
    if not content.strip():
        return jsonify({"error": "File is empty"}), 400
    
    file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    
    try:
        s3 = get_spaces_client()
        bucket = os.environ.get("SPACES_BUCKET")
        if bucket:
            s3.put_object(Bucket=bucket, Key=f"documents/{filename}", Body=content.encode())
    except Exception as e:
        app.logger.warning(f"Failed to upload to Spaces: {e}")
    
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO documents (filename, content, file_type) VALUES (%s, %s, %s) RETURNING id",
            (filename, content, file_type)
        )
        doc_id = cur.fetchone()[0]
        
        chunks = chunk_text(content)
        chunks_with_embeddings = 0
        
        for i, chunk_content in enumerate(chunks):
            embedding = get_embedding(chunk_content)
            
            if embedding:
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                cur.execute(
                    "INSERT INTO chunks (document_id, content, embedding, chunk_index) VALUES (%s, %s, %s::vector, %s)",
                    (doc_id, chunk_content, embedding_str, i)
                )
                chunks_with_embeddings += 1
            else:
                cur.execute(
                    "INSERT INTO chunks (document_id, content, chunk_index) VALUES (%s, %s, %s)",
                    (doc_id, chunk_content, i)
                )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "ok",
            "document_id": doc_id,
            "filename": filename,
            "chunks_created": len(chunks),
            "chunks_embedded": chunks_with_embeddings
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/documents/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM documents WHERE id = %s RETURNING filename", (doc_id,))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if result:
            try:
                s3 = get_spaces_client()
                bucket = os.environ.get("SPACES_BUCKET")
                if bucket:
                    s3.delete_object(Bucket=bucket, Key=f"documents/{result[0]}")
            except Exception:
                pass
            return jsonify({"status": "ok", "deleted": result[0]})
        else:
            return jsonify({"error": "Document not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================================================
# ROUTES: UTILITIES
# =============================================================================

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

@app.route("/api/search", methods=["POST"])
def search():
    """Direct semantic search endpoint."""
    init_schema()
    data = request.get_json()
    query = data.get("query", "").strip()
    top_k = data.get("top_k", RAG_TOP_K)
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
    results = retrieve_context(query, top_k)
    return jsonify({"results": results, "query": query})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
