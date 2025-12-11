# phash.py
import hashlib

import cv2
import numpy as np
from PIL import Image
import imagehash


def extract_video_phash(path: str, num_frames: int = 5) -> str:
    """
    Izračunava robustan perceptual hash preko više kadrova videa.
    """
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video file for pHash: {path}")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    if frame_count <= 0:
        frame_indices = [0]
    else:
        step = max(frame_count // (num_frames + 1), 1)
        frame_indices = [step * (i + 1) for i in range(num_frames)]

    hashes = []

    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        pil_img = Image.fromarray(gray)
        h = imagehash.phash(pil_img)  # 64-bit hash
        hashes.append(int(str(h), 16))  # čuvamo kao int

    cap.release()

    if not hashes:
        raise RuntimeError("Could not compute pHash – no frames readable")

    # Kombinuj više frejm hash-eva u jedan SHA-256
    buf = b"".join(h.to_bytes(8, "big", signed=False) for h in hashes)
    return hashlib.sha256(buf).hexdigest()
