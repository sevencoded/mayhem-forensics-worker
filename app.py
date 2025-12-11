import uuid
import os
from flask import Flask, request, jsonify
from utils import supabase

UPLOAD_DIR = "/data/slices"
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
        file_path = f"{UPLOAD_DIR}/{proof_id}.mp4"

        # snimi slice na disk
        file.save(file_path)

        # upiši proof
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": name,
            "hash": sha256,
            "signature": sha256
        }).execute()

        # queue job
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "file_path": file_path,
            "status": "pending"
        }).execute()

        return jsonify({"ok": True, "proof_id": proof_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
