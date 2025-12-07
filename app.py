import os
import asyncio
import tempfile
import subprocess
import numpy as np
from supabase import create_client
import requests

# --- Local forensic modules ---
from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash
from utils import save_spectrogram_png


# ================================
# SUPABASE CONFIG
# ================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

MAIN_BUCKET = "main_videos"


# ================================
# SAFE AUDIO LOADER (FFMPEG RAW PCM)
# ================================
def load_audio_with_ffmpeg(video_path):
    """
    Extracts mono 44.1kHz float32 PCM using FFmpeg into RAM.
    Works even if soundfile cannot read the audio.
    """

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-f", "f32le",
        "-acodec", "pcm_f32le",
        "-ac", "1",
        "-ar", "44100",
        "-vn",
        "-hide_banner",
        "-loglevel", "error",
        "pipe:1"
    ]

    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        raw_audio = p.stdout.read()
        p.stdout.close()
        p.wait()

        if len(raw_audio) < 5000:
            print("❌ FFmpeg extracted too little audio (corrupted or silent?)")
            return None, None

        audio = np.frombuffer(raw_audio, dtype=np.float32)
        return audio, 44100

    except Exception as e:
        print("❌ FFmpeg audio extraction failed:", e)
        return None, None


# ================================
# PROCESSING A SINGLE JOB
# ================================
async def process_job(job):
    proof_id = job["proof_id"]
    video_path = job["video_path"]
    user_id = job["user_id"]

    print(f"\n🔵 Processing job for proof {proof_id}")
    print("📁 Video path:", video_path)

    # -----------------------------
    # 1) DOWNLOAD VIDEO FROM STORAGE
    # -----------------------------
    try:
        data = supabase.storage.from_(MAIN_BUCKET).download(video_path)
    except Exception as e:
        print("❌ ERROR: Could not download video:", e)
        return

    # Save temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp.write(data)
    tmp.close()
    video_file = tmp.name

    print("📥 Downloaded →", video_file, "size:", os.path.getsize(video_file))

    # -----------------------------
    # 2) EXTRACT AUDIO
    # -----------------------------
    audio, sr = load_audio_with_ffmpeg(video_file)

    if audio is None:
        print("❌ FATAL: No usable audio extracted. Marking job as failed.")
        supabase.table("forensic_queue").update({"status": "failed"}).eq("id", job["id"]).execute()
        return

    print("🎧 Audio extracted → samples:", len(audio))

    # -----------------------------
    # 3) ENF FINGERPRINT
    # -----------------------------
    enf_hash, enf_conf, spect = extract_enf(audio, sr)
    print("🌀 ENF Hash:", enf_hash)

    spect_file = None
    if spect is not None:
        spect_file = f"{user_id}_{proof_id}_enf.png"
        save_spectrogram_png(spect, spect_file)

        supabase.storage.from_(MAIN_BUCKET).upload(
            f"enf/{spect_file}",
            open(spect_file, "rb"),
            {"content-type": "image/png"}
        )
        print("📤 ENF Spectrogram uploaded.")

    # -----------------------------
    # 4) AUDIO FINGERPRINT (spectral)
    # -----------------------------
    audio_fp = extract_audio_fingerprint(audio, sr)
    print("🎼 Audio FP:", audio_fp)

    # -----------------------------
    # 5) VIDEO PHASH
    # -----------------------------
    phash = extract_video_phash(video_file)
    print("🖼 pHash:", phash)

    # -----------------------------
    # 6) STORE RESULTS IN DATABASE
    # -----------------------------
    supabase.table("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fingerprint": audio_fp,
        "video_phash": phash,
        "metadata_hash": None,
        "chain_hash": None,
    }).execute()

    # -----------------------------
    # 7) MARK JOB DONE
    # -----------------------------
    supabase.table("forensic_queue").update({
        "status": "done"
    }).eq("id", job["id"]).execute()

    # -----------------------------
    # 8) DELETE ORIGINAL VIDEO
    # -----------------------------
    supabase.storage.from_(MAIN_BUCKET).remove([video_path])
    print("🗑 Removed original video from bucket.")

    print("✔ JOB COMPLETE\n")


# ================================
# MAIN LOOP
# ================================
async def loop():
    print("👀 Worker started. Waiting for jobs...")

    while True:
        jobs = supabase.table("forensic_queue").select("*").eq("status", "pending").execute().data

        if len(jobs) > 0:
            print("🟡 Found", len(jobs), "jobs.")
        else:
            print("… no jobs …")

        for job in jobs:
            await process_job(job)

        await asyncio.sleep(10)


# ================================
# ENTRY POINT
# ================================
if __name__ == "__main__":
    asyncio.run(loop())
