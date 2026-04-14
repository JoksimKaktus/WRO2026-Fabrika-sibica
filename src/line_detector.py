from picamera2 import Picamera2
import cv2
import numpy as np

# HSV threshold for blue color
lower_blue = np.array([0, 80, 60])
upper_blue = np.array([20, 255, 255])

# HSV threshold for orange color
lower_orange = np.array([110, 100, 140])
upper_orange = np.array([115, 255, 255])


def getArea(picam2, color, show_window=False): # 0 - orange , 1 - blue
    # Capture frame from camera
    frame = picam2.capture_array()

    # Safety check
    if frame is None or frame.size == 0:
        return 0

    # Convert to HSV
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Use only bottom half of image 
    h, w = frame_hsv.shape[:2]
    roi = frame_hsv[h // 2:, :]

    # Threshold mask depending on color
    mask = None
    if color == 0:
        mask = cv2.inRange(roi, lower_orange, upper_orange)
    else:
        mask = cv2.inRange(roi, lower_blue, upper_blue)

    # Remove noise
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Find contours (connected regions)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_area = 0
    best = None

    # Find best candidate contour
    for cnt in contours:
        area = cv2.contourArea(cnt)

        # Ignore small noise
        if area < 500:
            continue

        # Bounding box and shape ratio
        x, y, ww, hh = cv2.boundingRect(cnt)
        aspect = max(ww, hh) / (min(ww, hh) + 1)

        # Prefer long shapes (line-like objects)
        if aspect > 3 and area > best_area:
            best = cnt
            best_area = area

    # Optional debug window
    if show_window:
        display = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

        if best is not None:
            x, y, ww, hh = cv2.boundingRect(best)
            cv2.rectangle(display, (x, y), (x + ww, y + hh), (0, 255, 0), 2)

        cv2.imshow("Line", display)
        cv2.waitKey(1)

    # Return area of best detected line
    return best_area


# Example test
# picam2 = Picamera2()
# picam2.configure(picam2.create_preview_configuration())
# picam2.start()
#
# for i in range(10000):
#     print(getArea(picam2, 0, True))
