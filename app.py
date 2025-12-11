# app.py
import os
import uuid
import threading
from flask import Flask, request, jsonify

from utils import supabase
from worker import worker_loop

UPLOAD_DIR = "/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_id = request.form["user_id"]
        name = request.form["name"]
        sha256 = request.form["sha256"]
        file = request.files["file"]

        proof_id = str(uuid.uuid4())

        # Save slice on disk
        filepath = f"{UPLOAD_DIR}/{proof_id}.mp4"
        file.save(filepath)

        # Insert proof metadata
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": name,
            "hash": sha256,
            "signature": sha256
        }).execute()

        # Insert job for worker
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "file_path": filepath,
            "status": "pending"
        }).execute()

        return jsonify({"ok": True, "proof_id": proof_id}), 200

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def health():
    return "SERVER OK", 200


# LAUNCH FLASK + WORKER IN SAME SERVICE
if __name__ == "__main__":
    threading.Thread(target=worker_loop, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
