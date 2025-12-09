from flask import Flask, request, jsonify
import os
import uuid
from supabase import create_client

# -----------------------------------------------------------
# SUPABASE INIT
# -----------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

UPLOAD_DIR = "slices"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -----------------------------------------------------------
# UPLOAD ENDPOINT — samo snima slice i kreira queue task
# -----------------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload_slice():
    try:
        user_id = request.form["user_id"]
        name = request.form["name"]
        sha256 = request.form["sha256"]

        file = request.files["file"]
        proof_id = str(uuid.uuid4())

        # Save temporary slice
        filename = f"{proof_id}.mp4"
        filepath = os.path.join(UPLOAD_DIR, filename)
        file.save(filepath)

        # Insert into proofs
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "hash": sha256,
            "signature": sha256,
            "name": name
        }).execute()

        # Add to forensic queue
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": filepath,
            "status": "pending"
        }).execute()

        return jsonify({"status": "ok", "proof_id": proof_id})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def health():
    return "API running", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
