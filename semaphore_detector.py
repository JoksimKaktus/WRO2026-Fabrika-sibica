from picamera2 import Picamera2
import cv2
import time
import numpy as np

# GREEN
lower_green = np.array([45, 75, 105])
upper_green = np.array([85, 255, 255])

# RED
lower_red = np.array([100, 170, 100])
upper_red = np.array([122, 255, 255])

# NOT BLACK
noblack_low = np.array([1,1,1])
noblack_upp = np.array([255,255,255])


def getData(picam2):
    frame = picam2.capture_array()    # BGR image
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)


    mask_green = cv2.inRange(frame_hsv, lower_green, upper_green)
    mask_red = cv2.inRange(frame_hsv, lower_red, upper_red)


    result_green = cv2.bitwise_and(frame, frame, mask=mask_green)
    result_green = cv2.cvtColor(result_green, cv2.COLOR_BGR2RGB)      # RGB image, only green
    result_red = cv2.bitwise_and(frame, frame, mask=mask_red)
    result_red = cv2.cvtColor(result_red, cv2.COLOR_BGR2RGB)          # RGB image, only red

    bw_green = cv2.inRange(result_green, noblack_low, noblack_upp)    # Turning green into white
    bw_red = cv2.inRange(result_red, noblack_low, noblack_upp)        # Turning red into white

    # # SHOW FPS
    # curr_time = time.time()
    # fps = 1 / (curr_time - prev_time)
    # prev_time = curr_time
    # cv2.putText(frame_rgb, f"FPS: {int(fps)}", (10, 30),
    #             cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)  
    

    max_area = 0
    max_attr = [0,0,0,0,(0,0,0)]  # [x,y,w,h,(BGR)]


    # Find contours and draw rectangles around green object
    contours_g, _ = cv2.findContours(bw_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours_g:
        area = cv2.contourArea(c)
        # ignore tiny blobs/noise
        if area > 100 and area > max_area:
            x, y, w, h = cv2.boundingRect(c)
            if h >= w/2:
                max_area = area
                max_attr = [x,y,w,h,(0,255,0)]

    # Find contours and draw rectangles around red object     
    contours_r, _ = cv2.findContours(bw_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours_r:
        area = cv2.contourArea(c)
        # ignore tiny blobs/noise
        if area > 100 and area > max_area:
            x, y, w, h = cv2.boundingRect(c)
            if h >= w/2:
                max_area = area
                max_attr = [x,y,w,h,(0,0,255)]

    # 0 - green, 1 - red
    # center of semaphore
    # 0 - very far away, 1 - far away, 2 - middle, 3 - close, 4 - very close 
    ret = [-1,-1,-1] 

    if max_area > 0:
        x = max_attr[0]
        y = max_attr[1]
        w = max_attr[2]
        h = max_attr[3]
        color = max_attr[4]
        if color == (0,255,0):
            ret[0] = 0
        else:
            ret[0] = 1

        cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), color, 2)
        # print(x,y,w,h)
        new_x = (x-320)/320
        new_y = (y-240)/240
        new_w = w/640
        new_h = h/480
        # print(new_x, new_y, new_w, new_h)
        area_left = 0
        area_right = 0
        semaphore_center = (2*new_x + new_w)/2
        ret[1] = semaphore_center
        ret[2] = max_area

        #if max_area/(h * w)*100 < 0.6:
         #   return [-1,-1,-1]

    #cv2.imshow("Line", frame_rgb)
    #cv2.waitKey(1)

    return ret


    cv2.waitKey(1)

cv2.destroyAllWindows()


# picam2 = Picamera2()
# picam2.configure(picam2.create_preview_configuration())
# picam2.start()

# for i in range(10000):
#     print(getData(picam2))
