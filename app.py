import os
from flask import Flask, request, jsonify
from supabase import create_client
import uuid

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/upload", methods=["POST"])
def upload_slice():
    try:
        user_id = request.form.get("user_id")
        name = request.form.get("name")
        sha256_hash = request.form.get("sha256")

        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file"}), 400

        proof_id = str(uuid.uuid4())

        tmp_path = f"/tmp/{proof_id}_slice.mp4"
        file.save(tmp_path)

        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "hash": sha256_hash,
            "signature": sha256_hash,
            "name": name
        }).execute()

        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": tmp_path,
            "status": "pending"
        }).execute()

        return jsonify({"status": "queued", "proof_id": proof_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
