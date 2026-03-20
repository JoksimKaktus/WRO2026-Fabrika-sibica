from picamera2 import Picamera2
import cv2
import time
import numpy as np

# GREEN
lower_green = np.array([45, 75, 120])
upper_green = np.array([85, 150, 255])

# RED
lower_red = np.array([115, 180, 100])
upper_red = np.array([125, 255, 255])

# NOT BLACK
noblack_low = np.array([1,1,1])
noblack_upp = np.array([255,255,255])

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()
prev_time = 0


while True:
    frame = picam2.capture_array()    # BGR image
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)


    mask_green = cv2.inRange(frame_hsv, lower_green, upper_green)
    mask_red = cv2.inRange(frame_hsv, lower_red, upper_red)
    mask = cv2.bitwise_or(mask_green, mask_red)


    result_green = cv2.bitwise_and(frame, frame, mask=mask_green)
    result_green = cv2.cvtColor(result_green, cv2.COLOR_BGR2RGB)      # RGB image, only green
    result_green_hsv = cv2.cvtColor(result_green, cv2.COLOR_BGR2HSV)  # HSV image, only green
    result_red = cv2.bitwise_and(frame, frame, mask=mask_red)
    result_red = cv2.cvtColor(result_red, cv2.COLOR_BGR2RGB)          # RGB image, only red
    result_red_hsv = cv2.cvtColor(result_red, cv2.COLOR_BGR2HSV)      # HSV image, only red

    bw_green = cv2.inRange(result_green, noblack_low, noblack_upp)    # Turning green into white
    bw_red = cv2.inRange(result_red, noblack_low, noblack_upp)        # Turning red into white

    # SHOW FPS
    # curr_time = time.time()
    # fps = 1 / (curr_time - prev_time)
    # prev_time = curr_time
    # cv2.putText(frame_rgb, f"FPS: {int(fps)}", (10, 30),
    #             cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)  
    

    # Find contours and draw rectangles around green object
    contours_g, _ = cv2.findContours(bw_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours_g:
        area = cv2.contourArea(c)
        # ignore tiny blobs/noise
        if area > 750:
            x, y, w, h = cv2.boundingRect(c)
            if h >= w:
                cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Find contours and draw rectangles around red object     
    contours_r, _ = cv2.findContours(bw_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours_r:
        area = cv2.contourArea(c)
        # ignore tiny blobs/noise
        if area > 750:
            x, y, w, h = cv2.boundingRect(c)
            if h >= w:
                cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), (0, 0, 255), 2)


    cv2.imshow("Pi Camera", frame_rgb)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
