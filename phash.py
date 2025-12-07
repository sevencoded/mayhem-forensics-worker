import cv2
import numpy as np
from utils import sha256_bytes


def extract_video_phash(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    hashes = []
    frame_id = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # Skip frames for speed (take 1 every 15)
        if frame_id % 15 != 0:
            frame_id += 1
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (32, 32))

        dct = cv2.dct(np.float32(small))
        block = dct[:8, :8]  # low frequencies only

        hash_val = sha256_bytes(block.flatten().astype(np.float32).tobytes())
        hashes.append(hash_val)

        frame_id += 1

    cap.release()

    if len(hashes) == 0:
        return None

    # Combine all hashes → global video fingerprint
    joined = "|".join(hashes).encode()
    return sha256_bytes(joined)
