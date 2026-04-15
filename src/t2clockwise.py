# =========================
# IMPORTS
# =========================

import time
import math
import board
import threading
import busio as busio
import adafruit_vl53l0x
import adafruit_tca9548a
from smbus2 import SMBus
from gpiozero import (PWMOutputDevice, DigitalOutputDevice, AngularServo, Device, Button, Servo)
from gpiozero.pins.lgpio import LGPIOFactory
from mpu6050 import mpu6050
from line_detector import getArea
from picamera2 import Picamera2
from semaphore_detector import getData


# =========================
# GLOBALS / SETUP
# =========================

pressedStart = False       # Flag for start button
lastAngle = 0              # Last servo angle (used to avoid jitter)
timeOffset = 0             # Time compensation for sensor reset delays

Device.pin_factory = LGPIOFactory()

# Motor and servo pins
IN1 = 6
IN2 = 5
ENA = 13
SERVO_PIN = 19

# I2C multiplexer and MPU addresses
MUX_ADDR = 0x70
MUX_CHANNEL_3 = 0x08
I2C_BUS = 1
MPU_ADDR = 0x68

# XSHUT pins for resetting distance sensors
XSHUT_PINS = [8, 7, 1, 25]

# Motor control devices
IN1_dev = DigitalOutputDevice(IN1)
IN2_dev = DigitalOutputDevice(IN2)
ENA_pwm = PWMOutputDevice(ENA, frequency=1000)

# Servo for steering
servo = AngularServo(
    SERVO_PIN,
    min_angle=-90,
    max_angle=90,
    min_pulse_width=0.0005,
    max_pulse_width=0.0025,
    frame_width=0.02    
)

# Start button
button = Button(16, pull_up=True)

# Sensor reset control
xshuts = [DigitalOutputDevice(pin) for pin in XSHUT_PINS]

# Multiplexer
i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
tca = adafruit_tca9548a.TCA9548A(i2c, address=MUX_ADDR)

# Sensor index → multiplexer channel mapping
order = [0, 1, 4, 2]
sensors = [None] * 4

# Camera initialization
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()


# =========================
# HELPER FUNCTIONS
# =========================

def forward(speed):  # Move forward
    IN1_dev.off()
    IN2_dev.on()
    ENA_pwm.value = speed / 100


def reverse(speed):  # Move backward
    IN1_dev.on()
    IN2_dev.off()
    ENA_pwm.value = speed / 100


def stop():
    # Stop the robot and center steering
    ENA_pwm.value = 0
    servo.value = 0
    print("STOPPED")


def SetAngle(angle):
    # Set steering angle (-45 to 45 degrees)
    global lastAngle, targetAngle

    angle = max(angle, -45)
    angle = min(angle, 45)

    # Avoid tiny changes (reduces jitter)
    if abs(lastAngle - angle) < 2:
        return

    servo.angle = angle
    lastAngle = angle


def pressed():
    # Button press callback
    global numPressed, pressedStart
    print("Button press")
    pressedStart = True


def hard_reset_sensor(index):
    # Reset sensor using XSHUT pin
    try:
        xshuts[index].off()
        time.sleep(0.2)
        xshuts[index].on()
        time.sleep(0.3)
    except Exception as e:
        print(f"Failed hard reset on sensor {index}: {e}")


def init_sensor(index, channel):
    # Initialize sensor on selected mux channel
    global sensors

    for attempt in range(5):
        try:
            hard_reset_sensor(index)

            # Make sure I2C is free
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
            print(f"Init failed for sensor {index}: {e}")
            time.sleep(0.5)

    sensors[index] = None
    return False


def safe_read(sensor, timeout=0.10):
    # Read sensor value in a separate thread (prevents blocking)
    result = [None]

    def target():
        try:
            result[0] = sensor.range
        except:
            result[0] = None

    t = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join(timeout)

    # Timeout means sensor likely froze
    if t.is_alive():
        return None

    return result[0]


def read_sensor(index):
    # Safe sensor read with automatic recovery
    global sensors, timeOffset

    channel = order[index]

    # Initialize sensor if needed
    if sensors[index] is None:
        if not init_sensor(index, channel):
            return 8191

    value = safe_read(sensors[index])

    # Handle timeout (sensor failure)
    if value is None:
        print(f"[Sensor {index}] TIMEOUT → resetting")
        forward(0)

        t1 = time.perf_counter()
        sensors[index] = None

        # Hard reset
        try:
            xshuts[index].off()
            time.sleep(0.4)
            xshuts[index].on()
            time.sleep(0.4)
        except:
            pass

        time.sleep(0.5)

        # Reinitialize sensor
        if init_sensor(index, channel):
            value = safe_read(sensors[index])
            t2 = time.perf_counter()
            timeOffset += t2 - t1

            if value is not None:
                return value

        return 8191

    return value


def unpark():
    # Initial maneuver to leave starting position
    timeOfMove = 0.65
    speed = 40

    STATE = 0
    stateChange = time.perf_counter()
    limitOfMoves = 4

    while True:
        curTime = time.perf_counter()

        # Switch direction periodically
        if curTime - stateChange > timeOfMove:
            STATE = 1 - STATE
            stateChange = curTime
            limitOfMoves -= 1

            if limitOfMoves == 0:
                break

            stop()
            time.sleep(1.0)
            stateChange = time.perf_counter()

        if STATE == 0:
            forward(speed)
            SetAngle(45)
        else:
            reverse(speed)
            SetAngle(-45)


# =========================
# MAIN LOOP
# =========================

def main():
    global timeOffset

    # Movement parameters
    speed = 70
    distFromWall = 430
    distFromFront = 650

    # PD controller gains
    Kp = 0.08
    Kd = 0.4

    # Semaphore PD gains
    Kps = 0.4
    Kds = 0.4

    prevError = 0

    # State machine variables
    numOfTurns = 0
    corner = False
    lastLine = time.perf_counter()

    # States:
    # 0 = wall following
    # 1 = turning
    # 2 = semaphore approach
    # 3 = going around semaphore
    STATE = 0
    stateChange = time.perf_counter()

    turnTime = 1.2
    semSizeLimit = 20000

    # Timing for obstacle avoidance
    semTurnTimeGreen1 = 0.80
    semTurnTimeGreen2 = 1.00
    semTurnTimeRed1 = 0.60
    semTurnTimeRed2 = 1.20

    semTurnColor = -1

    # Start with unparking
    unpark()
    forward(speed)
    SetAngle(0)

    while True:
        curTime = time.perf_counter() - timeOffset

        # Read distance sensors
        distanceLeft = read_sensor(0)
        distanceFront = read_sensor(1)
        distanceRight = read_sensor(2)

        # Detect line (used for turns/laps)
        area = getArea(picam2, 0)
        if area > 0:
            lastLine = curTime
            corner = True
        else:
            if corner and curTime - lastLine > 0.8:
                if STATE == 0:
                    STATE = 1
                    stateChange = curTime
                corner = False
                numOfTurns += 1

        # Skip iteration if sensors failed
        if -1 in [distanceLeft, distanceFront, distanceRight]:
            time.sleep(0.1)
            continue

        # Get semaphore data
        (semColor, semCenter, semSize) = getData(picam2)

        # -------- STATE MACHINE --------
        if STATE == 0:
            if semColor != -1:
                STATE = 2
                prevError = 0
            elif distanceFront < distFromFront:
                STATE = 1

        elif STATE == 1:
            if semColor != -1:
                STATE = 2
                prevError = 0
            elif curTime - stateChange > turnTime:
                STATE = 0

        elif STATE == 2:
            if semColor == -1:
                STATE = 0
            elif semSize > semSizeLimit:
                semTurnColor = semColor
                STATE = 3
                stateChange = curTime

        elif STATE == 3:
            totalTurnTime = semTurnTimeRed1 + semTurnTimeRed2
            if semTurnColor == 0:
                totalTurnTime = semTurnTimeGreen1 + semTurnTimeGreen2

            if curTime - stateChange > totalTurnTime:
                STATE = 0

        # -------- CONTROL --------
        error = 0
        angle = 0

        if STATE == 0:
            error = distFromWall - distanceLeft
            angle = Kp * error + Kd * (error - prevError)

        elif STATE == 2:
            error = semCenter * 100
            angle = Kps * error + Kds * (error - prevError)

        # -------- ACTUATION --------
        if STATE == 0:
            SetAngle(angle if distanceLeft < 2000 else 0)

        elif STATE == 1:
            SetAngle(45)

        elif STATE == 2:
            SetAngle(angle)

        elif STATE == 3:
            if semTurnColor == 0:
                SetAngle(-45 if curTime - stateChange < semTurnTimeGreen1 else 45)
            else:
                SetAngle(45 if curTime - stateChange < semTurnTimeRed1 else -45)

        forward(speed)
        prevError = error
        time.sleep(0.03)

    stop()

# =========================
# SENSOR STARTUP
# =========================

# select_mux_channel_3()
# gyro = mpu6050(MPU_ADDR)

for i, ch in enumerate(order):
    init_sensor(i, ch)
    time.sleep(0.2)

# button callback
button.when_pressed = pressed


# Turn on LED to signal everything is ready
led.on()

time.sleep(1.0)

led.off()

# wait for start
try:
    while True:
        time.sleep(0.1)
        
        if pressedStart:
            pressedStart = False

            try:
                #threading.Thread(target=servo_worker, daemon=True).start()
                main()
                break
            except KeyboardInterrupt:
                print("Keyboard interrupt")
                break

            except Exception as e:
                print(f"Main loop crashed: {e}")
                stop()
                time.sleep(1)

except KeyboardInterrupt:
    print("Exiting program")

finally:
    cleanup()
