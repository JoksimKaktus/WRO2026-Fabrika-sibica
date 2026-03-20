from picamera2 import Picamera2
import cv2
import time
import numpy as np

# GREEN
lower_green = np.array([45, 75, 160])
upper_green = np.array([85, 150, 255])

# RED
lower_red = np.array([115, 180, 170])
upper_red = np.array([125, 255, 255])


picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()
prev_time = 0


while True:
    frame = picam2.capture_array()    # DAJE BGR SLIKU
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)


    mask_green = cv2.inRange(frame_hsv, lower_green, upper_green)
    mask_red = cv2.inRange(frame_hsv, lower_red, upper_red)

    mask = cv2.bitwise_or(mask_green, mask_red)


    result = cv2.bitwise_and(frame, frame, mask=mask)
    result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    bw = cv2.inRange(hsv, lower_green, upper_green)

    # SHOW FPS
    # curr_time = time.time()
    # fps = 1 / (curr_time - prev_time)
    # prev_time = curr_time
    # cv2.putText(result, f"FPS: {int(fps)}", (10, 30),
    #             cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)


    cv2.imshow("Pi Camera", result)

    if cv2.waitKey(1) & 0xFF == ord('q'):     # MORA cv2.waitKey() DA IMA
        break

cv2.destroyAllWindows()