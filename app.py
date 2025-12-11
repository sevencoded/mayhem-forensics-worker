import uuid
import os
import threading
import base64
from flask import Flask, request, jsonify

from utils import supabase
from worker import worker_loop

UPLOAD_DIR = "/data/slices"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# ----------------------
# START WORKER IN THREAD
# ----------------------
def start_worker_background():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()

start_worker_background()


# ----------------------
# UPLOAD ENDPOINT
# ----------------------
@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_id = request.form["user_id"]
        name = request.form["name"]
        sha256 = request.form["sha256"]
        file = request.files["file"]

        proof_id = str(uuid.uuid4())
        file_path = f"{UPLOAD_DIR}/{proof_id}.mp4"

        file.save(file_path)

        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": name,
            "hash": sha256,
            "signature": sha256,
        }).execute()

        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "file_path": file_path,
            "status": "pending",
        }).execute()

        return jsonify({"ok": True, "proof_id": proof_id})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def health():
    return "WEB+WORKER OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
