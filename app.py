from flask import Flask, request, jsonify
import os
import uuid
from supabase import create_client

# -----------------------------------------------------------
# LOAD ENV VARS (MUST EXIST)
# -----------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in Render environment!")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------------------------------------
# FLASK APP
# -----------------------------------------------------------
app = Flask(__name__)

UPLOAD_DIR = "/tmp/slices"      # SAFE for Render!
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -----------------------------------------------------------
# UPLOAD ENDPOINT
# -----------------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload_slice():
    try:
        # Validate inputs
        if "user_id" not in request.form:
            return jsonify({"error": "Missing user_id"}), 400

        user_id = request.form["user_id"]
        name = request.form.get("name", "Untitled")
        sha256 = request.form.get("sha256", None)

        if "file" not in request.files:
            return jsonify({"error": "Missing file"}), 400

        file = request.files["file"]

        # Generate proof ID
        proof_id = str(uuid.uuid4())

        # Save slice to /tmp (Render safe)
        filename = f"{proof_id}.mp4"
        filepath = os.path.join(UPLOAD_DIR, filename)
        file.save(filepath)

        print("✔ Slice saved:", filepath)

        # Insert into proofs
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "hash": sha256,
            "signature": sha256,
            "name": name
        }).execute()

        print("✔ Proof inserted:", proof_id)

        # Insert queue task
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": filepath,
            "status": "pending"
        }).execute()

        print("✔ Queue task created:", proof_id)

        return jsonify({"status": "ok", "proof_id": proof_id})

    except Exception as e:
        print("❌ UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def health():
    return "API running", 200


if __name__ == "__main__":
    print("🚀 Starting Flask API on port 10000...")
    app.run(host="0.0.0.0", port=10000)
