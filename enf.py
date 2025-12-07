import numpy as np
import librosa
from scipy.signal import correlate
from utils import sha256_bytes


def extract_enf(audio_data, sample_rate):
    """
    Extract ENF-like low frequency energy signature from audio.
    Works with raw PCM from ffmpeg.
    """

    # If audio too short → skip
    if audio_data is None or len(audio_data) < sample_rate * 0.2:
        return None, None, None

    # ENF is around 50 Hz → downsample to ~500 Hz
    target_sr = 500

    try:
        audio = librosa.resample(
            audio_data.astype(np.float32),
            orig_sr=sample_rate,
            target_sr=target_sr
        )
    except Exception:
        return None, None, None

    hop = 250
    win = 500

    try:
        S = np.abs(librosa.stft(audio, n_fft=win, hop_length=hop))
    except Exception:
        return None, None, None

    freqs = librosa.fft_frequencies(sr=target_sr, n_fft=win)

    enf_index = np.argmin(np.abs(freqs - 50))
    enf_series = S[enf_index]

    if len(enf_series) < 5:
        return None, None, None

    # Normalize
    enf_norm = enf_series - np.mean(enf_series)
    if np.all(enf_norm == 0):
        return None, None, None

    corr = correlate(enf_norm, enf_norm)
    confidence = float(np.max(corr) / len(enf_norm))

    # Hash only first 200 samples for stability
    digest_bytes = enf_series[:200].astype(np.float32).tobytes()
    enf_hash = sha256_bytes(digest_bytes)

    return enf_hash, confidence, S
