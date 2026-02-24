import os
import hashlib
from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import boto3
from botocore.client import Config
import requests

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

def call_inference(messages):
    """
    Call inference endpoint.
    Supports DigitalOcean GenAI agents or any OpenAI-compatible endpoint.
    """
    custom_endpoint = os.environ.get("GENAI_ENDPOINT", "")
    custom_key = os.environ.get("GENAI_API_KEY", "")
    model = os.environ.get("DEFAULT_MODEL", "")
    
    if custom_endpoint and custom_key:
        headers = {
            "Authorization": f"Bearer {custom_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7
        }
        
        if model:
            payload["model"] = model
        
        base_url = custom_endpoint.rstrip('/')
        
        paths_to_try = [
            "/api/v1/chat/completions",
            "/v1/chat/completions", 
            "/chat/completions",
            ""
        ]
        
        last_error = None
        for path in paths_to_try:
            try:
                url = f"{base_url}{path}"
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 404:
                    last_error = f"404 at {path}"
                    continue
                
                if response.status_code != 200:
                    return f"API error ({response.status_code}): {response.text[:300]}"
                
                data = response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0].get("message", {}).get("content", "No content in response")
                elif "response" in data:
                    return data["response"]
                elif "output" in data:
                    return data["output"]
                elif "error" in data:
                    return f"API error: {data['error']}"
                else:
                    return f"Unexpected response: {str(data)[:300]}"
                    
            except requests.exceptions.Timeout:
                return "Request timed out. The model may be loading - please try again."
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                continue
            except Exception as e:
                return f"Inference error: {str(e)}"
        
        return f"Could not connect to GenAI endpoint. Tried multiple paths. Last error: {last_error}"
    
    user_message = messages[-1].get("content", "") if messages else ""
    return f"[Demo Mode] You said: {user_message}\n\nTo enable AI, set GENAI_ENDPOINT and GENAI_API_KEY."

def get_cache_key(message):
    """Generate cache key from message."""
    return f"chat:{hashlib.md5(message.encode()).hexdigest()}"

def is_inference_configured():
    """Check if inference is configured."""
    return bool(os.environ.get("GENAI_ENDPOINT") and os.environ.get("GENAI_API_KEY"))

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
    
    if is_inference_configured():
        status["components"]["inference"] = "configured"
    else:
        status["components"]["inference"] = "demo mode (no GenAI endpoint)"
    
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
            "content": "You are a helpful AI assistant. Be concise and helpful."
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
