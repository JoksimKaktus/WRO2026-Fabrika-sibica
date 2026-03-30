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
        if area > 750 and area > max_area:
            x, y, w, h = cv2.boundingRect(c)
            if h >= w:
                max_area = area
                max_attr = [x,y,w,h,(0,255,0)]
                # cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Find contours and draw rectangles around red object     
    contours_r, _ = cv2.findContours(bw_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours_r:
        area = cv2.contourArea(c)
        # ignore tiny blobs/noise
        if area > 750 and area > max_area:
            x, y, w, h = cv2.boundingRect(c)
            if h >= w:
                max_area = area
                max_attr = [x,y,w,h,(0,0,255)]
                # cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), (0, 0, 255), 2)

    if max_area > 0:
        x = max_attr[0]
        y = max_attr[1]
        w = max_attr[2]
        h = max_attr[3]
        color = max_attr[4]
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
        if(semaphore_center > 0):
            if(semaphore_center < 0.5):
                print("Semafor je desno")
            else:
                print("Semafor je vrlo desno")
        else:
            if(semaphore_center > -0.5):
                print("Semafor je lijevo")
            else:
                print("Semafor je vrlo lijevo")
        
        if(max_area > 60000):
            print("Bas blizu")
        elif(max_area > 30000):
            print("Blizu")
        elif(max_area > 10000):
            print("Srednja razdaljina")
        elif(max_area > 5000):
            print("Daleko")
        else:
            print("Bas daleko")

        print(max_area/(h * w)*100,'%',"semafor")
        print("-----------------------------")



    cv2.imshow("Pi Camera", frame_rgb)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
