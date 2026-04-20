from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

@app.route("/")
def home():
    return "CampusBuzz AI backend is running on GKE 🚀"

@app.route("/env")
def env_check():
    return jsonify({
        "has_gemini_api_key": bool(GEMINI_API_KEY),
        "key_prefix": GEMINI_API_KEY[:10] if GEMINI_API_KEY else None
    })

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json or {}
    prompt = data.get("prompt", "")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(url, json=payload, timeout=60)

    if response.status_code != 200:
        return jsonify({
            "upstream_status": response.status_code,
            "upstream_body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        }), 500

    result = response.json()

    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"response": text})
    except Exception:
        return jsonify({
            "message": "Gemini returned an unexpected payload",
            "raw_response": result
        }), 500

@app.route("/cpu-burn")
def cpu_burn():
    seconds = int(request.args.get("seconds", 20))
    end = time.time() + seconds
    x = 0

    while time.time() < end:
        for i in range(10000):
            x += i * i

    return jsonify({
        "message": f"CPU burn completed for {seconds} seconds",
        "dummy_result": x
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
