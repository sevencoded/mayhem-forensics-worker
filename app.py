import os
import base64
from flask import Flask, request, jsonify
from supabase import create_client
import uuid

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_id = request.form.get("user_id")
        name = request.form.get("name")
        sha256_hash = request.form.get("sha256")

        file = request.files["file"]
        slice_bytes = file.read()

        # encode slice → store minimal data
        b64_slice = base64.b64encode(slice_bytes).decode()

        proof_id = str(uuid.uuid4())

        # Create proof
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "hash": sha256_hash,
            "signature": "N/A",
            "name": name,
        }).execute()

        # Insert queue job
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": b64_slice,
            "status": "pending",
        }).execute()

        return jsonify({"ok": True, "proof_id": proof_id})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500
