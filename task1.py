import time
import math
import board
import busio as busio
import adafruit_vl53l0x
import adafruit_tca9548a
from smbus2 import SMBus
from gpiozero import (PWMOutputDevice, DigitalOutputDevice, Servo, Device, Button)
from gpiozero.pins.lgpio import LGPIOFactory
from mpu6050 import mpu6050
from line_detector import getArea

# =========================
# GLOBALS / SETUP
# =========================

pressedStart = False

Device.pin_factory = LGPIOFactory()

IN1 = 6
IN2 = 5
ENA = 13
SERVO_PIN = 19

MUX_ADDR = 0x70
MUX_CHANNEL_3 = 0x08
I2C_BUS = 1
MPU_ADDR = 0x68

# Maybe later change from pin 1 to something else
XSHUT_PINS = [8, 7, 1, 25]

IN1_dev = DigitalOutputDevice(IN1)
IN2_dev = DigitalOutputDevice(IN2)
ENA_pwm = PWMOutputDevice(ENA, frequency=1000)
servo_pwm = PWMOutputDevice(SERVO_PIN, frequency=50)
button = Button(16, pull_up=True)

xshuts = [DigitalOutputDevice(pin) for pin in XSHUT_PINS]

# Slower I2C = much more stable
i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
tca = adafruit_tca9548a.TCA9548A(i2c, address=MUX_ADDR)

# sensor index -> mux channel
order = [0, 1, 4, 2]
sensors = [None] * 4


# =========================
# HELPER FUNCTIONS
# =========================

def select_mux_channel_3():
    with SMBus(I2C_BUS) as bus:
        bus.write_byte(MUX_ADDR, MUX_CHANNEL_3)
    time.sleep(0.01)


def disable_mux():
    with SMBus(I2C_BUS) as bus:
        bus.write_byte(MUX_ADDR, 0x00)
    time.sleep(0.01)


def forward(speed): # speed 0-100
    IN1_dev.off()
    IN2_dev.on()
    #ENA_pwm.value = speed / 100


def reverse(speed): # speed 0-100
    IN1_dev.on()
    IN2_dev.off()
    ENA_pwm.value = speed / 100


def stop(): 
    ENA_pwm.value = 0


def SetAngle(angle): # from -1 to 1, -1 - left, 0 - straight, 1 - right
    pulse_ms = 1.5 + (angle * 0.5)

    # 50Hz = 20ms period
    duty_cycle = pulse_ms / 20.0

    servo_pwm.value = duty_cycle


def pressed():  # button has been pressed
    global numPressed, pressedStart
    print("Button press")
    pressedStart = True


def hard_reset_sensor(index): # sometimes sensors fail, this resets them
    try:
        xshuts[index].off()
        time.sleep(0.2)
        xshuts[index].on()
        time.sleep(0.3)
    except Exception as e:
        print(f"Failed hard reset on sensor {index}: {e}")


def init_sensor(index, channel):
    global sensors

    for attempt in range(5):
        try:
            hard_reset_sensor(index)

            try:
                if i2c.try_lock():
                    i2c.unlock()
            except:
                pass

            time.sleep(0.1)

            sensors[index] = adafruit_vl53l0x.VL53L0X(tca[channel])

            sensors[index].measurement_timing_budget = 33000

            print(f"Sensor {index} on mux channel {channel} initialized")
            return True

        except Exception as e:
            print(
                f"Init failed for sensor {index} "
                f"(channel {channel}) attempt {attempt + 1}: {e}"
            )
            time.sleep(0.5)

    sensors[index] = None
    return False


def read_sensor(index):
    global sensors

    channel = order[index]

    if sensors[index] is None:
        print(f"Sensor {index} not initialized, reinitializing...")
        if not init_sensor(index, channel):
            return -1

    try:
        value = sensors[index].range
        time.sleep(0.02)
        return value

    except OSError as e: 
        print(f"Read failed on sensor {index}: {e}")

        # recover from random I2C failure
        try:
            try:
                if i2c.try_lock():
                    i2c.unlock()
            except:
                pass

            disable_mux()
            time.sleep(0.05)

            if init_sensor(index, channel):
                value = sensors[index].range
                time.sleep(0.02)
                return value

        except Exception as e2:
            print(f"Recovery failed on sensor {index}: {e2}")

        return -1

    except Exception as e:
        print(f"Unexpected sensor error on sensor {index}: {e}")
        return -1


# =========================
# MAIN LOOP
# =========================

def main():
    distFromWall = 330
    speed = 70
    errorLimit = 40
    wallReverseDist = 70
    stateChange = time.perf_counter()

    # 0 - NORMAL
    # 1 - WALL IN FRONT
    STATE = 0

    # 0 - clockwise
    # 1 - counterclockwise
    # 2 - didnt figure out yet 
    direction = 2

    numOfTurns = 0
    lastLine = time.perf_counter()
    corner = False

    while True:
        curTime = time.perf_counter()

        distanceLeft = read_sensor(0)
        distanceFront = read_sensor(1)
        distanceRight = read_sensor(2)
        distanceBack = read_sensor(3)

        select_mux_channel_3()
        gyro_data = gyro.get_gyro_data()
        xRot = gyro_data["x"]+2.65   # adding average error when stationary

        # Skip this loop if one of the sensors failed
        if -1 in [distanceLeft, distanceFront, distanceRight, distanceBack]:
            print("One or more sensors unavailable, retrying...")
            time.sleep(0.1)
            continue

        if direction == 2:
            if distanceLeft > 2000:
                direction = 1
            elif distanceRight > 2000:
                direction = 0

        # print(
        #     f"L:{distanceLeft} "
        #     f"F:{distanceFront} "
        #     f"R:{distanceRight} "
        #     f"B:{distanceBack}"
        # )

        error = 0

        if direction == 0:
            error = (distFromWall - distanceRight) / 20  # calculate error from the wall
        elif direction == 1:
            error = (distFromWall - distanceLeft) / 20  # calculate error from the wall

        error = (distFromWall - distanceLeft) / 20  

        if error < -errorLimit:  # limiting
            error = -errorLimit
        if error > errorLimit:
            error = errorLimit

        angle = (math.exp(error / 18) - 1) / (math.exp(error / 18) + 1)  # func for steering

        SetAngle(angle)


        if(STATE == 0): # NORMAL
            if distanceFront <= wallReverseDist:
                STATE = 1
                reverse(speed)
                stateChange = time.perf_counter()
            else:
                forward(speed)
        elif(STATE == 1): # WALL IN FRONT
            if(curTime - stateChange > 2.0):
                STATE = 0
                forward(speed)
            else:
                reverse(speed)

        area = getArea()

        if area > 0:
            lastLine = curTime
            corner = True
        else:
            if corner and curTime - lastLine > 1.0:
                corner = False
                numOfTurns += 1
                print(numOfTurns)
                


        time.sleep(0.01)

    stop()
    print("Stopped")

# =========================
# SENSOR STARTUP
# =========================

select_mux_channel_3()
gyro = mpu6050(MPU_ADDR)

for i, ch in enumerate(order):
    init_sensor(i, ch)
    time.sleep(0.2)

# button callback
button.when_pressed = pressed

# wait for start
while True:
    time.sleep(0.1)

    if pressedStart:
        try:
            main()
        except KeyboardInterrupt:
            stop()
            break
        except Exception as e:
            print(f"Main loop crashed: {e}")
            stop()
            time.sleep(1)