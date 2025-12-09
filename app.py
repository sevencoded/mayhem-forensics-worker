from flask import Flask, request, jsonify
import os
import uuid
from supabase import create_client

# -----------------------------------------------------------
# SUPABASE INIT
# -----------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE environment variables")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------------------------------------
# SHARED DISK DIRECTORY
# -----------------------------------------------------------
UPLOAD_DIR = "/data/files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# -----------------------------------------------------------
# UPLOAD ENDPOINT
# -----------------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload_slice():
    try:
        user_id = request.form["user_id"]
        name = request.form.get("name", "Untitled")
        sha256 = request.form.get("sha256", "")
        file = request.files["file"]

        proof_id = str(uuid.uuid4())
        filepath = f"{UPLOAD_DIR}/{proof_id}.mp4"

        file.save(filepath)
        print("✔ Slice saved:", filepath)

        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "hash": sha256,
            "signature": sha256,
            "name": name
        }).execute()

        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": filepath,
            "status": "pending"
        }).execute()

        print("✔ Queue task created:", proof_id)
        return jsonify({"status": "ok", "proof_id": proof_id})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/")
def health():
    return "API running", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
