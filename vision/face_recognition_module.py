"""
vision/face_recognition.py

Face recognition — the realistic "neural network" piece. This does NOT
train a new network from scratch; it uses a pretrained face-embedding
network (via the `face_recognition` library, built on dlib's ResNet).

How it actually works:
1. A photo of a face goes through the neural network, which outputs
   128 numbers (a "face embedding") — a numeric fingerprint of that face.
2. To recognize someone, we compare a new face's 128 numbers against
   everyone stored in memory, using distance between the number-lists.
3. Closest match under a threshold = recognized. No match = unknown person.

This connects directly to memory/history_store.py's face_embedding column.
"""
import face_recognition
import numpy as np
import pickle
import memory.history_store as history

MATCH_THRESHOLD = 0.6  # lower = stricter matching, 0.6 is the standard default


def encode_face_from_image(image_path: str):
    """
    Loads an image file and returns its face embedding (128 numbers).
    Returns None if no face is found in the image.
    """
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        return None
    return encodings[0]  # assumes one main face per photo


def encode_face_from_frame(frame):
    """
    Same as above, but takes a live webcam frame (numpy array) instead
    of a file path — used for real-time recognition.
    """
    encodings = face_recognition.face_encodings(frame)
    if not encodings:
        return None
    return encodings[0]


def register_person(name: str, image_path: str, notes: str = "") -> bool:
    """
    Learns a new person: encodes their face and stores it in memory
    under their name. Returns True if successful.
    """
    encoding = encode_face_from_image(image_path)
    if encoding is None:
        return False

    embedding_bytes = pickle.dumps(encoding)
    history.add_person(name=name, notes=notes, face_embedding=embedding_bytes)
    return True


def identify_face(encoding) -> dict:
    """
    Compares a face encoding against everyone stored in memory.
    Returns {"name": str, "confidence": float} or {"name": None} if unknown.
    """
    people = history.get_all_people()
    known_encodings = []
    known_names = []

    for person in people:
        if person["face_embedding"] is None:
            continue
        stored_encoding = pickle.loads(person["face_embedding"])
        known_encodings.append(stored_encoding)
        known_names.append(person["name"])

    if not known_encodings:
        return {"name": None, "confidence": 0.0}

    distances = face_recognition.face_distance(known_encodings, encoding)
    best_match_index = int(np.argmin(distances))
    best_distance = distances[best_match_index]

    if best_distance <= MATCH_THRESHOLD:
        confidence = round((1 - best_distance) * 100, 1)
        name = known_names[best_match_index]
        history.mark_person_seen(name)
        return {"name": name, "confidence": confidence}

    return {"name": None, "confidence": 0.0}


def identify_from_image(image_path: str) -> dict:
    """Convenience wrapper: photo file -> identification result, in one call."""
    encoding = encode_face_from_image(image_path)
    if encoding is None:
        return {"name": None, "confidence": 0.0, "error": "No face detected in image"}
    return identify_face(encoding)