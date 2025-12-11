# app_web.py
import uuid
import os
from flask import Flask, request, jsonify
from utils import supabase, upload_file

app = Flask(__name__)

@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_id = request.form["user_id"]
        name = request.form["name"]
        sha256 = request.form["sha256"]
        file = request.files["file"]

        slice_bytes = file.read()
        proof_id = str(uuid.uuid4())

        # 1️⃣ Snimi slice u Supabase Storage (više ne ide u bazu)
        storage_path = f"{user_id}/{proof_id}_slice.mp4"

        upload_file(
            path=storage_path,
            data=slice_bytes,
            mime="video/mp4"
        )

        # 2️⃣ Upis u proofs
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": name,
            "hash": sha256,
            "signature": sha256
        }).execute()

        # 3️⃣ Queue job – umesto video_data sada se čuva samo path
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": storage_path,
            "status": "pending"
        }).execute()

        return jsonify({"ok": True, "proof_id": proof_id}), 200

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def health():
    return "WEB OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
