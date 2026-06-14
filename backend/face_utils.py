import pickle
from io import BytesIO

import face_recognition
import numpy as np
from PIL import Image


def encode_face(image_bytes: bytes) -> np.ndarray:
    image = face_recognition.load_image_file(BytesIO(image_bytes))
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        raise ValueError("No face detected in the image")
    return encodings[0]


def compare_faces(stored_blob: bytes, live_bytes: bytes, tolerance: float = 0.6) -> bool:
    stored_encoding = pickle.loads(stored_blob)
    live_image = face_recognition.load_image_file(BytesIO(live_bytes))
    live_encodings = face_recognition.face_encodings(live_image)
    if not live_encodings:
        raise ValueError("No face detected in the image")
    results = face_recognition.compare_faces([stored_encoding], live_encodings[0], tolerance=tolerance)
    return bool(results[0])
