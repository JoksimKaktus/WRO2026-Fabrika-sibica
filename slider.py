from picamera2 import Picamera2
import cv2
import numpy as np

def nothing(x):
    pass

# Create window for sliders
cv2.namedWindow("Controls")
cv2.resizeWindow("Controls", 500, 300)

# Trackbars for HSV lower/upper bounds
cv2.createTrackbar("H min", "Controls", 115, 179, nothing)
cv2.createTrackbar("H max", "Controls", 125, 179, nothing)
cv2.createTrackbar("S min", "Controls", 180, 255, nothing)
cv2.createTrackbar("S max", "Controls", 255, 255, nothing)
cv2.createTrackbar("V min", "Controls", 170, 255, nothing)
cv2.createTrackbar("V max", "Controls", 255, 255, nothing)

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()

while True:
    frame = picam2.capture_array()

    # If capture_array() is BGR in your setup, keep this:
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Read slider values
    h_min = cv2.getTrackbarPos("H min", "Controls")
    h_max = cv2.getTrackbarPos("H max", "Controls")
    s_min = cv2.getTrackbarPos("S min", "Controls")
    s_max = cv2.getTrackbarPos("S max", "Controls")
    v_min = cv2.getTrackbarPos("V min", "Controls")
    v_max = cv2.getTrackbarPos("V max", "Controls")

    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])

    mask = cv2.inRange(frame_hsv, lower, upper)
    result = cv2.bitwise_and(frame, frame, mask=mask)
    result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)

    # Optional: show values on screen
    text = f"L: [{h_min},{s_min},{v_min}] U: [{h_max},{s_max},{v_max}]"
    cv2.putText(result, text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    cv2.imshow("Result", result)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

cv2.destroyAllWindows()

