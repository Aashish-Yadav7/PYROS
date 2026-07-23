"""
register_face_test.py

Run this once to test face registration:  python register_face_test.py
Takes a photo from your webcam, saves your face under your name.
"""
import cv2
import face_recognition
import vision.face_recognition_module as face_db

name = input("Enter your name to register: ").strip()

cam = cv2.VideoCapture(0)
print("Look at the camera... taking photo in 3 seconds")
import time
time.sleep(3)
ret, frame = cam.read()
cam.release()

if not ret:
    print("Failed to capture from webcam.")
else:
    cv2.imwrite("temp_face.jpg", frame)
    success = face_db.register_person(name, "temp_face.jpg")
    if success:
        print(f"Registered {name} successfully! Try running recognize_once() now.")
    else:
        print("No face detected in the photo — try again with better lighting.")