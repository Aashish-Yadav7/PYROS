"""
register_face_test.py

Run this to register your face:  python register_face_test.py
Shows a LIVE camera preview window so you can see yourself before the
photo is taken. Press SPACE to capture, or 'q' to cancel.
"""
import cv2
import vision.face_recognition_module as face_db

name = input("Enter your name to register: ").strip()

cam = cv2.VideoCapture(0)
if not cam.isOpened():
    print("Could not access webcam.")
    exit()

print("Camera preview open. Press SPACE to take the photo, or 'q' to cancel.")

captured_frame = None
while True:
    ret, frame = cam.read()
    if not ret:
        print("Failed to read from webcam.")
        break

    preview = cv2.flip(frame, 1)
    cv2.putText(preview, "Press SPACE to capture, Q to cancel", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
    cv2.imshow("PYROS - Register Face", preview)

    key = cv2.waitKey(1) & 0xFF
    if key == ord(" "):
        captured_frame = frame
        break
    elif key == ord("q"):
        print("Cancelled.")
        break

cam.release()
cv2.destroyAllWindows()

if captured_frame is not None:
    cv2.imwrite("temp_face.jpg", captured_frame)
    success = face_db.register_person(name, "temp_face.jpg")
    if success:
        print(f"Registered {name} successfully!")
    else:
        print("No face detected in the photo — try again with better lighting, facing the camera directly.")