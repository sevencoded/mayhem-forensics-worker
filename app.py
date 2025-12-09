import os
import uuid
import traceback
from flask import Flask, request, jsonify
from supabase import create_client
import tempfile
from utils import upload_file

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

        if not user_id or not name or not sha256:
            return jsonify({"error": "Missing fields"}), 400

        file = request.files.get("file")
        if not file:
            return jsonify({"error": "Missing video slice"}), 400

        # temporarily save slice
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tmp.write(file.read())
        tmp.close()
        slice_path = tmp.name

        # new proof id
        proof_id = str(uuid.uuid4())

        # upload slice to Supabase storage
        storage_path = f"slices/{user_id}_{proof_id}.mp4"
        with open(slice_path, "rb") as f:
            upload_file(storage_path, f.read(), "video/mp4")

        # create proof entry (metadata only)
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": name,
            "hash": sha256
        }).execute()

        # queue forensic task
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": storage_path,
            "status": "pending"
        }).execute()

        os.remove(slice_path)

        return jsonify({"ok": True, "proof_id": proof_id}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
