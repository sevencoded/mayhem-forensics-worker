import io
import hashlib
import numpy as np
import librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _extract_enf_series(y, sr):
    n_fft = 2048
    hop = int(sr * 0.5)
    spec = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    def band_energy(fc):
        b = (freqs >= fc - 1) & (freqs <= fc + 1)
        return spec[b].mean() if b.any() else 0

    energies = {50: band_energy(50), 60: band_energy(60)}
    mains = max(energies, key=energies.get)

    band = (freqs >= mains - 1) & (freqs <= mains + 1)
    idxs = np.where(band)[0]
    if not len(idxs):
        idxs = np.where(freqs <= 80)[0]

    band_spec = spec[idxs, :]
    peaks = idxs[band_spec.argmax(axis=0)]
    enf_series = freqs[peaks]

    return enf_series, spec, freqs, mains


def extract_enf(path):
    y, sr = librosa.load(path, sr=1000, mono=True, duration=120.0)
    if y.size == 0:
        raise ValueError("Empty audio for ENF")

    enf_series, spec, freqs, mains = _extract_enf_series(y, sr)

    enf_series = enf_series.astype(np.float32)
    enf_series -= enf_series.mean()
    std = enf_series.std() or 1.0
    enf_series /= std
    enf_hash = hashlib.sha256(enf_series.tobytes()).hexdigest()

    spec_db = 20 * np.log10(spec + 1e-6)
    low = freqs <= 80
    spec_low = spec_db[low]
    freqs_low = freqs[low]

    fig, ax = plt.subplots(figsize=(6, 2))
    ax.imshow(
        spec_low,
        origin="lower",
        aspect="auto",
        extent=[0, spec_low.shape[1], freqs_low[0], freqs_low[-1]],
    )
    ax.set_title(f"ENF ~{mains} Hz")
    ax.axis("off")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buf.seek(0)

    return enf_hash, buf.getvalue()
