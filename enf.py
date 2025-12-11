# enf.py
import io
import hashlib

import numpy as np
import librosa
import matplotlib
matplotlib.use("Agg")  # za headless servere (Render)
import matplotlib.pyplot as plt


def _extract_enf_series(y: np.ndarray, sr: int, mains_freq_candidates=(50.0, 60.0)):
    """
    Izvlači ENF-like seriju:
    - fokus na band oko 50/60 Hz
    - po frame-u dominantni bin u tom bandu
    """
    if y.size == 0:
        raise ValueError("Empty audio signal passed to ENF extractor")

    n_fft = 2048
    hop_length = int(sr * 0.5)  # ~0.5s između frame-ova

    spec = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # Odaberi da li je 50 ili 60 Hz dominantan
    def band_energy(center: float) -> float:
        band = (freqs >= center - 1.0) & (freqs <= center + 1.0)
        if not np.any(band):
            return 0.0
        return spec[band].mean()

    energies = {f: band_energy(f) for f in mains_freq_candidates}
    mains_freq = max(energies, key=energies.get)

    band = (freqs >= mains_freq - 1.0) & (freqs <= mains_freq + 1.0)
    band_idxs = np.where(band)[0]
    if band_idxs.size == 0:
        # fallback: ceo low band do 80 Hz
        band = freqs <= 80.0
        band_idxs = np.where(band)[0]

    band_spec = spec[band_idxs, :]

    # po frame-u uzmi bin sa max energijom u bandu
    peak_idxs = band_idxs[band_spec.argmax(axis=0)]
    enf_series = freqs[peak_idxs]

    return enf_series, spec, freqs, mains_freq


def extract_enf(video_path: str):
    """
    Ekstrakcija ENF-like hash-a i PNG vizualizacije iz audio trake videa.
    """
    # Limit na 120s audio zbog performansi
    y, sr = librosa.load(video_path, sr=1000, mono=True, duration=120.0)

    if y.size == 0:
        raise ValueError(f"Empty/invalid audio when loading file: {video_path}")

    enf_series, spec, freqs, mains_freq = _extract_enf_series(y, sr)

    # Normalizacija ENF serije i hash
    enf_series = enf_series.astype(np.float32)
    enf_series -= enf_series.mean()
    std = enf_series.std()
    if std == 0:
        std = 1.0
    enf_series /= std

    enf_hash = hashlib.sha256(enf_series.tobytes()).hexdigest()

    # PNG – low-frequency spektrogram (0–80 Hz)
    spec_db = 20.0 * np.log10(spec + 1e-6)

    max_freq = 80.0
    low_band = freqs <= max_freq
    spec_db_low = spec_db[low_band, :]
    freqs_low = freqs[low_band]

    fig, ax = plt.subplots(figsize=(6, 2))
    ax.imshow(
        spec_db_low,
        origin="lower",
        aspect="auto",
        extent=[0, spec_db_low.shape[1], freqs_low[0], freqs_low[-1]],
    )
    ax.set_ylim(freqs_low[0], freqs_low[-1])
    ax.set_title(f"Low-frequency spectrogram (ENF ~{int(mains_freq)} Hz)")
    ax.axis("off")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buf.seek(0)

    return enf_hash, buf.getvalue()
