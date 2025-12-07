import numpy as np
import librosa
from scipy.signal import correlate
from .utils import save_spectrogram_png

def extract_enf(audio_data, sample_rate):
    # Downsample (ENF is < 200 Hz)
    target_sr = 500
    audio = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=target_sr)

    # FFT windows
    hop = 250
    win = 500
    S = np.abs(librosa.stft(audio, n_fft=win, hop_length=hop))

    # ENF fundamental around 50 Hz
    freqs = librosa.fft_frequencies(sr=target_sr, n_fft=win)
    enf_index = np.argmin(np.abs(freqs - 50))
    enf_series = S[enf_index]

    if len(enf_series) < 3:
        return None, None, None  # too short

    # Confidence = autocorrelation peak
    corr = correlate(enf_series - np.mean(enf_series), enf_series - np.mean(enf_series))
    confidence = float(np.max(corr) / len(enf_series))

    # Hash ENF values
    enf_hash = str(abs(hash(tuple(enf_series[:100]))))  # 100 samples digest

    # Return spectrogram matrix
    return enf_hash, confidence, S
