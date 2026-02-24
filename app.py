import os
import hashlib
from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import boto3
from botocore.client import Config
from openai import OpenAI

app = Flask(__name__)

def get_pg_connection():
    """Get PostgreSQL connection using environment variables."""
    return psycopg2.connect(
        host=os.environ.get("PG_HOST"),
        port=os.environ.get("PG_PORT", 25060),
        database=os.environ.get("PG_DATABASE", "kb"),
        user=os.environ.get("PG_USER"),
        password=os.environ.get("PG_PASSWORD"),
        sslmode="require"
    )

def get_valkey_client():
    """Get Valkey client using environment variables (Redis-compatible)."""
    return redis.Redis(
        host=os.environ.get("VALKEY_HOST"),
        port=int(os.environ.get("VALKEY_PORT", 25061)),
        password=os.environ.get("VALKEY_PASSWORD"),
        ssl=True
    )

def get_spaces_client():
    """Get Spaces (S3-compatible) client."""
    session = boto3.session.Session()
    return session.client(
        "s3",
        region_name=os.environ.get("SPACES_REGION", "nyc3"),
        endpoint_url=f"https://{os.environ.get('SPACES_REGION', 'nyc3')}.digitaloceanspaces.com",
        aws_access_key_id=os.environ.get("SPACES_ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("SPACES_SECRET_KEY"),
        config=Config(signature_version="s3v4")
    )

def get_inference_client():
    """Get OpenAI-compatible client for DigitalOcean GenAI."""
    base_url = os.environ.get("GENAI_ENDPOINT", "")
    api_key = os.environ.get("GENAI_API_KEY", "")
    
    if not base_url or not api_key:
        return None
    
    return OpenAI(
        base_url=base_url,
        api_key=api_key
    )

def call_inference(messages):
    """Call DigitalOcean GenAI serverless inference."""
    client = get_inference_client()
    model = os.environ.get("DEFAULT_MODEL", "llama-3.1-70b-instruct")
    
    if not client:
        return "AI inference not configured. Set GENAI_ENDPOINT and GENAI_API_KEY environment variables."
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1024,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Inference error: {str(e)}"

def get_cache_key(message):
    """Generate cache key from message."""
    return f"chat:{hashlib.md5(message.encode()).hexdigest()}"

@app.route("/")
def index():
    """Serve the chat interface."""
    return render_template("index.html")

@app.route("/health")
def health():
    """Health check endpoint."""
    status = {"status": "healthy", "components": {}}
    
    try:
        conn = get_pg_connection()
        conn.close()
        status["components"]["postgres"] = "connected"
    except Exception as e:
        status["components"]["postgres"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    try:
        vk = get_valkey_client()
        vk.ping()
        status["components"]["valkey"] = "connected"
    except Exception as e:
        status["components"]["valkey"] = f"error: {str(e)}"
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
        status["components"]["spaces"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    genai_endpoint = os.environ.get("GENAI_ENDPOINT", "")
    genai_key = os.environ.get("GENAI_API_KEY", "")
    if genai_endpoint and genai_key:
        status["components"]["genai"] = "configured"
    else:
        status["components"]["genai"] = "not configured"
        status["status"] = "degraded"
    
    return jsonify(status)

@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle chat messages."""
    data = request.get_json()
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    cache_key = get_cache_key(user_message)
    
    try:
        vk = get_valkey_client()
        cached_response = vk.get(cache_key)
        if cached_response:
            return jsonify({
                "response": cached_response.decode("utf-8"),
                "cached": True
            })
    except Exception:
        pass
    
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant powered by DigitalOcean GenAI. Be concise and helpful."
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    
    response_text = call_inference(messages)
    
    try:
        vk = get_valkey_client()
        vk.setex(cache_key, 3600, response_text)
    except Exception:
        pass
    
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                user_message TEXT,
                assistant_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute(
            "INSERT INTO chat_history (user_message, assistant_response) VALUES (%s, %s)",
            (user_message, response_text)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass
    
    return jsonify({
        "response": response_text,
        "cached": False
    })

@app.route("/api/history", methods=["GET"])
def history():
    """Get chat history from PostgreSQL."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT user_message, assistant_response, created_at 
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
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })
        
        return jsonify({"history": history_list})
    except Exception as e:
        return jsonify({"error": str(e), "history": []})

@app.route("/api/clear-cache", methods=["POST"])
def clear_cache():
    """Clear the Valkey cache."""
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
