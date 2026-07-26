"""
vision/face_recognition_module.py

Face recognition using a pretrained face-embedding neural network.
"""
import face_recognition
import numpy as np
import pickle
import memory.history_store as history

MATCH_THRESHOLD = 0.6


def encode_face_from_image(image_path: str):
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        return None
    return encodings[0]


def encode_face_from_frame(frame):
    encodings = face_recognition.face_encodings(frame)
    if not encodings:
        return None
    return encodings[0]


def register_person(name: str, image_path: str, notes: str = "") -> bool:
    encoding = encode_face_from_image(image_path)
    if encoding is None:
        return False
    embedding_bytes = pickle.dumps(encoding)
    history.add_person(name=name, notes=notes, face_embedding=embedding_bytes)
    return True


def identify_face(encoding) -> dict:
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
    encoding = encode_face_from_image(image_path)
    if encoding is None:
        return {"name": None, "confidence": 0.0, "error": "No face detected in image"}
    return identify_face(encoding)