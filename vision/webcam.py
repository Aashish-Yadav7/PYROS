"""
vision/webcam.py

Live webcam face recognition — recognizes people in real time through
your camera, using the same face database built in vision/face_recognition.py.

Two ways to use this:
1. recognize_once() — grabs a single frame, identifies who's in it, returns
   immediately. Good for "who am I looking at right now" type requests.
2. start_live_recognition() — keeps the camera open and continuously
   identifies faces, printing/announcing names as it sees them, until you
   press 'q' to quit. Good for a background "greet people as they appear" mode.
"""
import cv2
import face_recognition
import vision.face_recognition_module as face_db  # the file from before, with identify_face()


def recognize_once(camera_index: int = 0) -> dict:
    """
    Opens the webcam, grabs one frame, tries to identify the face in it,
    then closes the camera. Returns {"name": ..., "confidence": ...}
    or {"name": None} if no face / no match found.
    """
    cam = cv2.VideoCapture(camera_index)
    if not cam.isOpened():
        return {"name": None, "confidence": 0.0, "error": "Could not access webcam"}

    ret, frame = cam.read()
    cam.release()

    if not ret:
        return {"name": None, "confidence": 0.0, "error": "Failed to capture frame"}

    # OpenCV uses BGR color order, face_recognition expects RGB — convert first
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_frame)

    if not encodings:
        return {"name": None, "confidence": 0.0, "error": "No face detected"}

    return face_db.identify_face(encodings[0])


def start_live_recognition(camera_index: int = 0, on_recognized=None):
    """
    Keeps the webcam open and continuously identifies faces frame by frame.
    on_recognized: optional callback function, called as on_recognized(name)
    whenever someone new is recognized — this is where you'd hook in a
    voice greeting later ("Hey Aashish!").
    Press 'q' in the video window to stop.
    """
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

            # draw a box and label on the video feed, like real face-ID apps do
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