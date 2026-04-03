from picamera2 import Picamera2
import cv2
import numpy as np

# BLUE threshold
lower_blue = np.array([0, 80, 60])
upper_blue = np.array([20, 255, 255])

lower_orange = np.array([110, 100, 140])
upper_orange = np.array([115, 255, 255])


def getArea(picam2, color, show_window=False): # 0 - orange , (1,2) - blue
    frame = picam2.capture_array()

    if frame is None or frame.size == 0:
        return 0

    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Only bottom half
    h, w = frame_hsv.shape[:2]
    roi = frame_hsv[h // 2:, :]

    # Threshold
    mask = None

    if color == 0:
        mask = cv2.inRange(roi, lower_orange, upper_orange)
    else:
        mask = cv2.inRange(roi, lower_blue, upper_blue)

    # Clean noise
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_area = 0
    best = None

    for cnt in contours:
        area = cv2.contourArea(cnt)

        if area < 500:
            continue

        x, y, ww, hh = cv2.boundingRect(cnt)
        aspect = max(ww, hh) / (min(ww, hh) + 1)

        if aspect > 3 and area > best_area:
            best = cnt
            best_area = area

    if show_window:
        display = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

        if best is not None:
            x, y, ww, hh = cv2.boundingRect(best)
            cv2.rectangle(display, (x, y), (x + ww, y + hh), (0, 255, 0), 2)

        cv2.imshow("Line", display)
        cv2.waitKey(1)

    return best_area

# picam2 = Picamera2()
# picam2.configure(picam2.create_preview_configuration())
# picam2.start()

# for i in range(10000):
#     print(getArea(picam2, 0, True))