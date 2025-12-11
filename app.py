import uuid
import os
from flask import Flask, request, jsonify
from utils import supabase
from worker import worker_loop
import threading

app = Flask(__name__)

UPLOAD_DIR = "/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_id = request.form["user_id"]
        name = request.form["name"]
        sha256 = request.form["sha256"]
        file = request.files["file"]

        slice_bytes = file.read()

        proof_id = str(uuid.uuid4())
        local_path = f"{UPLOAD_DIR}/{proof_id}.mp4"

        # Save slice to disk
        with open(local_path, "wb") as f:
            f.write(slice_bytes)

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
            "file_path": local_path,
            "status": "pending"
        }).execute()

        return jsonify({"ok": True, "proof_id": proof_id}), 200

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def health():
    return "WEB OK", 200


# Run worker in the same container
if __name__ == "__main__":
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
