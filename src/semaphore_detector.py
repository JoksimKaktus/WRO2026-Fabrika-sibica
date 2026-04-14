from picamera2 import Picamera2
import cv2
import time
import numpy as np

# HSV range for GREEN detection
lower_green = np.array([50, 75, 125])
upper_green = np.array([85, 255, 255])

# HSV range for RED detection
lower_red = np.array([100, 170, 100])
upper_red = np.array([122, 255, 255])

# Range used to convert any non-black pixel into white
noblack_low = np.array([1,1,1])
noblack_upp = np.array([255,255,255])


def getData(picam2):
    # Capture frame (BGR format)
    frame = picam2.capture_array()

    # Convert to RGB and HSV 
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Create masks for green and red colors
    mask_green = cv2.inRange(frame_hsv, lower_green, upper_green)
    mask_red = cv2.inRange(frame_hsv, lower_red, upper_red)

    # Extract only green pixels
    result_green = cv2.bitwise_and(frame, frame, mask=mask_green)
    result_green = cv2.cvtColor(result_green, cv2.COLOR_BGR2RGB)

    # Extract only red pixels
    result_red = cv2.bitwise_and(frame, frame, mask=mask_red)
    result_red = cv2.cvtColor(result_red, cv2.COLOR_BGR2RGB)

    # Convert colored regions to binary
    bw_green = cv2.inRange(result_green, noblack_low, noblack_upp)
    bw_red = cv2.inRange(result_red, noblack_low, noblack_upp)

    # ================= FPS =================
    # curr_time = time.time()
    # fps = 1 / (curr_time - prev_time)
    # prev_time = curr_time
    # cv2.putText(frame_rgb, f"FPS: {int(fps)}", (10, 30),
    #             cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)  

    max_area = 0
    max_attr = [0,0,0,0,(0,0,0)]  # [x, y, w, h, color]

    # -------- GREEN OBJECT DETECTION --------
    contours_g, _ = cv2.findContours(bw_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours_g:
        area = cv2.contourArea(c)

        # Ignore small noise
        if area > 750 and area > max_area:
            x, y, w, h = cv2.boundingRect(c)

            # Prefer roughly vertical objects
            if h >= w and area/(h * w)*100 < 0.6:
                max_area = area
                max_attr = [x,y,w,h,(0,255,0)]

    # -------- RED OBJECT DETECTION --------
    contours_r, _ = cv2.findContours(bw_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours_r:
        area = cv2.contourArea(c)

        # Ignore small noise
        if area > 750 and area > max_area:
            x, y, w, h = cv2.boundingRect(c)

            # Prefer roughly vertical objects
            if h >= w and area/(h * w)*100 < 0.6:
                max_area = area
                max_attr = [x,y,w,h,(0,0,255)]

    # Return format:
    # ret[0] = color (0 = green, 1 = red, -1 = none)
    # ret[1] = horizontal position (from -1 to 1)
    # ret[2] = area (used for distance estimation)
    ret = [-1,-1,-1]

    # -------- PROCESS BEST DETECTION --------
    if max_area > 0:
        x, y, w, h, color = max_attr

        # Determine detected color
        if color == (0,255,0):
            ret[0] = 0
        else:
            ret[0] = 1

        # Draw bounding box
        cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), color, 2)

        # Normalize position and size
        new_x = (x-320)/320
        new_y = (y-240)/240
        new_w = w/640
        new_h = h/480

        # Calculate center position of object
        semaphore_center = (2*new_x + new_w)/2

        # Save position and area
        ret[1] = semaphore_center
        ret[2] = max_area

        # Quality check
        # if max_area/(h * w)*100 < 0.6:
        #     return [-1,-1,-1]

    # Debug display
    # cv2.imshow("Line", frame_rgb)
    # cv2.waitKey(1)

    return ret

    cv2.waitKey(1)

cv2.destroyAllWindows()


# Example test
# picam2 = Picamera2()
# picam2.configure(picam2.create_preview_configuration())
# picam2.start()
#
# for i in range(10000):
#     print(getData(picam2))