import librosa
import numpy as np
import hashlib

def generate_audio_fingerprint(filepath):
    y, sr = librosa.load(filepath, sr=None)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    fp = hashlib.sha256(onset.tobytes()).hexdigest()
    return fp
