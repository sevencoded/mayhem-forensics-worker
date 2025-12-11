# app_web.py
import uuid
import base64
import os
from flask import Flask, request, jsonify
from utils import supabase

app = Flask(__name__)

@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_id = request.form["user_id"]
        name = request.form["name"]
        sha256 = request.form["sha256"]
        file = request.files["file"]

        # Read slice bytes
        video_bytes = file.read()

        # Encode to base64 so Supabase can store it safely in JSON
        video_b64 = base64.b64encode(video_bytes).decode("utf-8")

        proof_id = str(uuid.uuid4())

        # Insert into proofs table
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": name,
            "hash": sha256,
            "signature": sha256
        }).execute()

        # Insert into forensic queue
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_data": video_b64,
            "status": "pending"
        }).execute()

        return jsonify({"ok": True, "proof_id": proof_id}), 200

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def health():
    return "WEB OK", 200


# Render requires this to keep server open
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
