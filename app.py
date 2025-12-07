import os
import asyncio
import tempfile
import ffmpeg
from supabase import create_client
import soundfile as sf
import numpy as np

# Lokalni moduli
from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash
from utils import save_spectrogram_png

# ENV promenljive
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

MAIN_BUCKET = "main_videos"


# -----------------------------------------
# AUDIO EXTRACTION (FFMPEG)
# -----------------------------------------
def extract_audio_from_mp4(video_path):
    audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name

    (
        ffmpeg
        .input(video_path)
        .output(audio_path, format='wav', ac=1, ar=44100)  # mono, 44.1 kHz
        .overwrite_output()
        .run(quiet=True)
    )

    return audio_path


# -----------------------------------------
# PROCESS JOB
# -----------------------------------------
async def process_job(job):
    proof_id = job["proof_id"]
    video_path = job["video_path"]
    user_id = job["user_id"]

    print("🔵 Processing", proof_id)

    # 1) Download video file
    resp = supabase.storage.from_(MAIN_BUCKET).download(video_path)
    if resp is None:
        print("❌ ERROR: Could not download video:", video_path)
        return

    # Save video to temp file
    tmp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp_video.write(resp)
    tmp_video.close()
    video_file = tmp_video.name

    # 2) Extract WAV audio from MP4
    audio_file = extract_audio_from_mp4(video_file)

    # 3) Load extracted WAV
    audio, sr = sf.read(audio_file)

    # ---------- ENF ----------
    enf_hash, enf_conf, spect = extract_enf(audio, sr)

    spect_file = None
    if spect is not None:
        spect_file = f"{user_id}_{proof_id}_enf.png"
        save_spectrogram_png(spect, spect_file)

        supabase.storage.from_(MAIN_BUCKET).upload(
            f"enf/{spect_file}",
            open(spect_file, "rb"),
            {"content-type": "image/png"}
        )

    # ---------- AUDIO FINGERPRINT ----------
    audio_fp = extract_audio_fingerprint(audio, sr)

    # ---------- VIDEO PHASH ----------
    phash = extract_video_phash(video_file)

    # ---------- Insert forensic results ----------
    supabase.table("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fingerprint": audio_fp,
        "video_phash": phash,
        "metadata_hash": None,
        "chain_hash": None
    }).execute()

    # Mark job done
    supabase.table("forensic_queue").update({"status": "done"}).eq("id", job["id"]).execute()

    # Remove original uploaded video
    supabase.storage.from_(MAIN_BUCKET).remove([video_path])

    print("✔ Done", proof_id)


# -----------------------------------------
# MAIN LOOP
# -----------------------------------------
async def loop():
    while True:
        jobs = supabase.table("forensic_queue").select("*").eq("status", "pending").execute().data
        for job in jobs:
            await process_job(job)

        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(loop())
