import os
import uuid
from flask import Flask, request, jsonify
from utils import supabase

UPLOAD_DIR = "/data/files"
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
        filepath = f"{UPLOAD_DIR}/{proof_id}.mp4"
        file.save(filepath)

        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": name,
            "hash": sha256,
            "signature": sha256
        }).execute()

        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": filepath,
            "status": "pending"
        }).execute()

        return jsonify({"ok": True, "proof_id": proof_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def health():
    return "WEB API OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
