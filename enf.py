import numpy as np
import librosa
from scipy.signal import correlate
from utils import sha256_bytes

def extract_enf(audio_data, sample_rate):
    if audio_data is None or len(audio_data) < sample_rate * 0.5:
        return None, None, None

    target_sr = 400  # nisko radi brže
    try:
        audio = librosa.resample(audio_data.astype(np.float32),
                                 orig_sr=sample_rate,
                                 target_sr=target_sr)
    except:
        return None, None, None

    hop = 200
    win = 400

    try:
        S = np.abs(librosa.stft(audio, n_fft=win, hop_length=hop))
    except:
        return None, None, None

    freqs = librosa.fft_frequencies(sr=target_sr, n_fft=win)
    idx = np.argmin(np.abs(freqs - 50))

    enf_series = S[idx]
    if len(enf_series) < 5:
        return None, None, None

    norm = enf_series - np.mean(enf_series)
    if np.all(norm == 0):
        return None, None, None

    corr = correlate(norm, norm)
    confidence = float(np.max(corr) / len(norm))

    digest = sha256_bytes(enf_series[:150].astype(np.float32).tobytes())
    return digest, confidence, S
