import os
import subprocess
import asyncio
import tempfile
from supabase import create_client
import soundfile as sf

from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash
from utils import save_spectrogram_png

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def extract_audio_wav(input_video):
    """Extract audio track from MP4 using ffmpeg → WAV file"""
    wav_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name

    cmd = [
        "ffmpeg",
        "-i", input_video,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-f", "wav",
        wav_path
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return wav_path

async def process_job(job):
    proof_id = job["proof_id"]
    video_path = job["video_path"]
    user_id = job["user_id"]

    print("🔵 Processing", proof_id)

    # DOWNLOAD VIDEO
    bucket = "main_videos"
    video_bytes = supabase.storage.from_(bucket).download(video_path)

    temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_video.write(video_bytes)
    temp_video.close()
    video_file = temp_video.name

    # 🔥 1) Extract audio properly (fix)
    wav_file = await extract_audio_wav(video_file)

    # Read WAV now (soundfile works)
    audio, sr = sf.read(wav_file)

    # ===== ENF =====
    enf_hash, enf_conf, spect = extract_enf(audio, sr)

    if spect is not None:
        png_name = f"{user_id}_{proof_id}_enf.png"
        save_spectrogram_png(spect, png_name)
        supabase.storage.from_(bucket).upload(
            f"enf/{png_name}",
            open(png_name, "rb"),
            {"content-type": "image/png"}
        )

    # ===== AUDIO FINGERPRINT =====
    audio_fp = extract_audio_fingerprint(audio, sr)

    # ===== VIDEO PHASH =====
    video_phash = extract_video_phash(video_file)

    supabase.table("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fingerprint": audio_fp,
        "video_phash": video_phash,
        "metadata_hash": None,
        "chain_hash": None,
    }).execute()

    supabase.table("forensic_queue").update(
        {"status": "done"}
    ).eq("id", job["id"]).execute()

    print("✔ Done", proof_id)


async def loop():
    while True:
        jobs = supabase.table("forensic_queue").select("*").eq("status", "pending").execute().data

        for job in jobs:
            await process_job(job)

        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(loop())
