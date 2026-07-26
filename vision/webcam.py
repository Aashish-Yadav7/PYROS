"""
vision/webcam.py

Live webcam face recognition using the face database above.
"""
import cv2
import face_recognition
import vision.face_recognition_module as face_db


def recognize_once(camera_index: int = 0) -> dict:
    cam = cv2.VideoCapture(camera_index)
    if not cam.isOpened():
        return {"name": None, "confidence": 0.0, "error": "Could not access webcam"}

    ret, frame = cam.read()
    cam.release()

    if not ret:
        return {"name": None, "confidence": 0.0, "error": "Failed to capture frame"}

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_frame)

    if not encodings:
        return {"name": None, "confidence": 0.0, "error": "No face detected"}

    return face_db.identify_face(encodings[0])


def start_live_recognition(camera_index: int = 0, on_recognized=None):
    cam = cv2.VideoCapture(camera_index)
    if not cam.isOpened():
        print("Could not access webcam.")
        return

    last_seen_name = None
    print("Live recognition started. Press 'q' in the video window to stop.")

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for (top, right, bottom, left), encoding in zip(face_locations, encodings):
            result = face_db.identify_face(encoding)
            name = result["name"] or "Unknown"

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 200, 0), 2)
            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)

            if name != "Unknown" and name != last_seen_name:
                last_seen_name = name
                if on_recognized:
                    on_recognized(name)

        cv2.imshow("PYROS - Live Recognition (press q to quit)", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cam.release()
    cv2.destroyAllWindows()