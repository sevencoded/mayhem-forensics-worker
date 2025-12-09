import os
import uuid
from flask import Flask, request, jsonify
from supabase import create_client
from datetime import datetime

# ----------------------------------------
# INIT
# ----------------------------------------
app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

QUEUE_DIR = "queue_slices"
os.makedirs(QUEUE_DIR, exist_ok=True)


# ----------------------------------------
# /upload endpoint
# ----------------------------------------
@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_id = request.form.get("user_id")
        name = request.form.get("name")
        sha256_hash = request.form.get("sha256")
        file = request.files.get("file")

        if not user_id or not name or not sha256_hash or not file:
            return jsonify({"error": "Missing fields"}), 400

        # ----------------------------------------
        # 1. Create new proof record
        # ----------------------------------------
        proof_id = str(uuid.uuid4())

        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "hash": sha256_hash,
            "signature": "auto",
            "name": name,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # ----------------------------------------
        # 2. Save slice to local queue folder
        # ----------------------------------------
        slice_path = f"{QUEUE_DIR}/{proof_id}.mp4"
        file.save(slice_path)

        # ----------------------------------------
        # 3. Add job to forensic queue
        # ----------------------------------------
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": slice_path,
            "status": "pending"
        }).execute()

        return jsonify({"status": "queued", "proof_id": proof_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------------------
# ROOT
# ----------------------------------------
@app.route("/")
def home():
    return "AI-Proof Forensics API Running"


# ----------------------------------------
# RUN
# ----------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
