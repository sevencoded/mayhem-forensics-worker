import os
import uuid
import tempfile
from flask import Flask, request, jsonify
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_id = request.form.get("user_id")
        name = request.form.get("name")
        sha256 = request.form.get("sha256")
        slice_bytes = request.form.get("slice_bytes")

        file = request.files.get("file")
        if not file:
            return jsonify({"error": "Missing file"}), 400

        # Save slice to temp
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tmp.write(file.read())
        tmp.close()

        local_path = tmp.name
        proof_id = str(uuid.uuid4())

        # Create proof entry
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": name,
            "hash": sha256,
            "signature": str(uuid.uuid4()),
        }).execute()

        # Add to queue
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": local_path,
            "status": "pending",
        }).execute()

        return jsonify({
            "ok": True,
            "queued": True,
            "proof_id": proof_id
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
