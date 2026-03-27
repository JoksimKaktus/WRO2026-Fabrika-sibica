import time
import board
import busio as busio
import adafruit_vl53l0x
import adafruit_tca9548a
from smbus2 import SMBus
from mpu6050 import mpu6050
from gpiozero import PWMOutputDevice, DigitalOutputDevice, Servo, Device, Button
from gpiozero.pins.lgpio import LGPIOFactory
import math
# from picamera2 import Picamera2
# import cv2
# import numpy as np

numPressed = 0

#SETUP VARIABLES

Device.pin_factory = LGPIOFactory()

IN1 = 6
IN2 = 5
ENA = 13
servo_pin = 19
MUX_ADDR = 0x70
MUX_CHANNEL_3 = 0x08
I2C_BUS = 1
MPU_ADDR = 0x68


IN1_dev = DigitalOutputDevice(IN1)
IN2_dev = DigitalOutputDevice(IN2)
ENA_pwm = PWMOutputDevice(ENA, frequency=1000)

servo = Servo(servo_pin)

button = Button(16, pull_up=True)

def select_mux_channel_3():
    with SMBus(I2C_BUS) as bus:
        bus.write_byte(MUX_ADDR, MUX_CHANNEL_3)
        time.sleep(0.01)

def disable_mux():
    with SMBus(I2C_BUS) as bus:
        bus.write_byte(MUX_ADDR, 0x00)
        time.sleep(0.01)

def forward(speed):
    IN1_dev.off()
    IN2_dev.on()
    ENA_pwm.value = speed / 100  # 0–100 → 0–1

def reverse(speed):
    IN1_dev.on()
    IN2_dev.off()
    ENA_pwm.value = speed / 100

def stop():
    ENA_pwm.value = 0

def SetAngle(angle):
    servo.value = angle  # maps to -1 to +1

def pressed():
    global numPressed
    print("Button press")
    numPressed += 1
    main()

def hard_reset_sensor(i):
    XSHUT_PINS = [8, 7, 1, 25]
    xshuts = [DigitalOutputDevice(pin) for pin in XSHUT_PINS]
    xshuts[i].off()
    time.sleep(0.4)
    xshuts[i].on()
    time.sleep(0.4)

def main():
    distFromWall = 300
    speed = 38
    errorLimit = 15

    while True:
        distanceLeft = sensors[0].range
        distanceFront = sensors[1].range
        distanceRight = sensors[2].range
        distanceBack = sensors[3].range

        print(f"L:{distanceLeft} F:{distanceFront} R:{distanceRight} B:{distanceBack}")
        forward(speed)

        error = (distFromWall - distanceLeft)/10
        print(error)
        if(error < -errorLimit):
            error = -errorLimit
        if(error > errorLimit):
            error = errorLimit
        angle = (math.exp(error/10)-1)/((math.exp(error/10)+1))
        SetAngle(angle)
        
        if distanceBack < 52 and distanceFront < 40:
            break
    
    stop()
    print("Stopped")

i2c = busio.I2C(board.SCL, board.SDA)
tca = adafruit_tca9548a.TCA9548A(i2c, address=0x70)

order = [0, 1, 4, 2]
sensors = [None] * 4

for i, ch in enumerate(order):
    for attempt in range(3):
        try:
            sensors[i] = adafruit_vl53l0x.VL53L0X(tca[ch])
            print(f"Sensor {i} (channel {ch}) initialized")
            break
        except Exception as e:
            print(f"Sensor {i} failed, retry {attempt+1}")
            hard_reset_sensor(i)
            time.sleep(0.5)
    else:
        print(f"Sensor {i} completely failed!")
    
    time.sleep(0.5)

# # Gyroscope
# select_mux_channel_3()
# sensor = mpu6050(MPU_ADDR)

button.when_pressed = pressed  # set ONCE

while True:
    time.sleep(1) 
    if numPressed > 1:
        break