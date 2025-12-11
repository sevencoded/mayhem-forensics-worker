# audio_fp.py
import hashlib
import numpy as np
import librosa


def extract_audio_fingerprint(path: str) -> str:
    """
    Deterministički audio fingerprint baziran na log-mel spektrogramu.

    - Downsample na 11.025 Hz mono
    - Mel-spektrogram (64 bendova)
    - Prosek preko vremena → kompaktan deskriptor
    - SHA-256 hash deskriptora
    """
    # Limit na ~60s zbog performansi
    y, sr = librosa.load(path, sr=11025, mono=True, duration=60.0)

    if y.size == 0:
        raise ValueError(f"Empty audio when loading file: {path}")

    # Mel-spektrogram
    S = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_fft=2048,
        hop_length=512,
        n_mels=64,
        power=2.0,
    )

    # Log skala (dB)
    S_db = librosa.power_to_db(S + 1e-9, ref=np.max)

    # Prosek po vremenu (axis=1 → po bendu)
    descriptor = S_db.mean(axis=1).astype(np.float32)

    # Normalizacija (ne-zavisno od apsolutne glasnoće)
    descriptor -= descriptor.mean()
    std = descriptor.std()
    if std == 0:
        std = 1.0
    descriptor /= std

    # Hash
    return hashlib.sha256(descriptor.tobytes()).hexdigest()
