import os
import base64
from flask import Flask, request, jsonify
from supabase import create_client, Client
import uuid

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

@app.route("/upload", methods=["POST"])
def upload_video():
    try:
        user_id = request.form.get("user_id")
        name = request.form.get("name")
        sha256_hash = request.form.get("sha256")

        file = request.files["file"]
        slice_bytes = file.read()

        # encode slice to base64
        b64_slice = base64.b64encode(slice_bytes).decode()

        proof_id = str(uuid.uuid4())

        # insert new proof
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "hash": sha256_hash,
            "signature": "N/A",
            "name": name,
        }).execute()

        # insert job with BASE64 slice data
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": b64_slice,  # now video data is here
            "status": "pending",
        }).execute()

        return jsonify({"success": True, "proof_id": proof_id})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500
