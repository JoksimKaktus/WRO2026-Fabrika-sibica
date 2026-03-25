import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
servo = 19

GPIO.setup(servo, GPIO.OUT)
pwm = GPIO.PWM(servo, 50)
pwm.start(0)

def SetAngle(angle):    # 100 middle, 50-150 range, 50 - left, 150 - right
    duty = angle / 18 + 2
    pwm.ChangeDutyCycle(duty)

while True:
    SetAngle(90)
    time.sleep(2.0)