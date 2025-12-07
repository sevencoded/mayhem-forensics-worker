import cv2
import numpy as np
from .utils import sha256_bytes

def extract_video_phash(video_path):
    cap = cv2.VideoCapture(video_path)
    hashes = []

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (32, 32))

        dct = cv2.dct(np.float32(resized))
        h = sha256_bytes(dct[:8, :8].flatten().tobytes())
        hashes.append(h)

    cap.release()

    # Combine all frame hashes
    joined = "".join(hashes).encode()
    return sha256_bytes(joined)
