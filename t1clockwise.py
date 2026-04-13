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


# =========================
# GLOBALS / SETUP
# =========================

pressedStart = False       # start flag from button
lastAngle = 0              # last servo angle (for smoothing)
timeOffset = 0             # compensates time lost during sensor resets

Device.pin_factory = LGPIOFactory()

# Motor + servo pins
IN1 = 6
IN2 = 5
ENA = 13
SERVO_PIN = 19

# I2C + multiplexer
MUX_ADDR = 0x70
MUX_CHANNEL_3 = 0x08
I2C_BUS = 1
MPU_ADDR = 0x68

# XSHUT pins (sensor reset pins)
XSHUT_PINS = [8, 7, 1, 25]

# Motor control setup
IN1_dev = DigitalOutputDevice(IN1)
IN2_dev = DigitalOutputDevice(IN2)
ENA_pwm = PWMOutputDevice(ENA, frequency=1000)

# Servo setup (steering)
servo = AngularServo(
    SERVO_PIN,
    min_angle=-90,
    max_angle=90,
    min_pulse_width=0.0005,
    max_pulse_width=0.0025,
    frame_width=0.02    
)

# Button input
button = Button(16, pull_up=True)

# XSHUT devices
xshuts = [DigitalOutputDevice(pin) for pin in XSHUT_PINS]

# Multiplexer
i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
tca = adafruit_tca9548a.TCA9548A(i2c, address=MUX_ADDR)

# Sensor order (index → mux channel)
order = [0, 1, 4, 2]
sensors = [None] * 4

# Camera setup
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()


# =========================
# HELPER FUNCTIONS
# =========================

def forward(speed): # speed 0-100
    # drive forward
    IN1_dev.off()
    IN2_dev.on()
    ENA_pwm.value = speed / 100


def reverse(speed): # speed 0-100
    # drive backward
    IN1_dev.on()
    IN2_dev.off()
    ENA_pwm.value = speed / 100


def stop(): 
    # stop motor + center steering
    ENA_pwm.value = 0
    servo.value = 0
    print("STOPPED")

def cleanup():
    # safely release all hardware resources
    stop()

    try:
        IN1_dev.close()
    except:
        pass
    try:
        IN2_dev.close()
    except:
        pass
    try:
        ENA_pwm.close()
    except:
        pass
    try:
        servo.close()
    except:
        pass
    try:
        button.close()
    except:
        pass
    for dev in xshuts:
        try:
            dev.close()
        except:
            pass


def SetAngle(angle):
    # set steering angle (-45 to 45), ignore tiny changes
    global lastAngle, targetAngle
    angle = max(angle,-45)
    angle = min(angle, 45)
    if abs(lastAngle - angle) < 2:
        return
    servo.angle = angle
    lastAngle = angle


def pressed():
    # button press callback
    global numPressed, pressedStart
    print("Button press")
    pressedStart = True


def hard_reset_sensor(index):
    # power cycle sensor via XSHUT pin
    try:
        xshuts[index].off()
        time.sleep(0.2)
        xshuts[index].on()
        time.sleep(0.3)
    except Exception as e:
        print(f"Failed hard reset on sensor {index}: {e}")


def init_sensor(index, channel):
    # initialize VL53L0X sensor on given mux channel
    global sensors

    for attempt in range(5):
        try:
            hard_reset_sensor(index)

            # ensure I2C is free
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
            print(f"Init failed for sensor {index} (channel {channel}) attempt {attempt + 1}: {e}")
            time.sleep(0.5)

    sensors[index] = None
    return False


def safe_read(sensor, timeout=0.10):
    # threaded read with timeout (prevents blocking)
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

    if t.is_alive():
        return None
    return result[0]


def read_sensor(index):
    # robust sensor read with auto-recovery
    global sensors,timeOffset

    channel = order[index]

    # initialize if missing
    if sensors[index] is None:
        if not init_sensor(index, channel):
            return 8191

    value = safe_read(sensors[index])

    # handle timeout (sensor freeze)
    if value is None:
        print(f"[Sensor {index}] TIMEOUT → resetting")
        forward(0)
        t1 = time.perf_counter()

        sensors[index] = None

        # hard reset
        try:
            xshuts[index].off()
            time.sleep(0.4)
            xshuts[index].on()
            time.sleep(0.4)
        except:
            pass

        time.sleep(0.5)

        if init_sensor(index, channel):
            value = safe_read(sensors[index])
            t2 = time.perf_counter()
            timeOffset += t2-t1
            if value is not None:
                return value
            else:
                return 8191

    return value


def restart_system():
    # full system reset (sensors + servo)
    global sensors, servo, order

    stop()
    time.sleep(0.2)

    for i, ch in enumerate(order):
        sensors[i] = None
        init_sensor(i, ch)

    try:
        servo.close()
    except:
        pass

    servo = AngularServo(
        SERVO_PIN,
        min_angle=-90,
        max_angle=90,
        min_pulse_width=0.0005, 
        max_pulse_width=0.0025,  
        frame_width=0.02    
    )

    servo.angle = 0
    time.sleep(0.2)


# =========================
# MAIN LOOP
# =========================

def main():
    global timeOffset

    # control parameters
    speed = 70
    distFromWall = 250
    distFromFront = 650
    Kp = 0.08
    Kd = 0.4
    prevError = 0

    numOfTurns = 0
    corner = False
    lastLine = time.perf_counter()
    line12 = 0
    timeToStop = 5.0

    # state machine: 0 = normal, 1 = turning
    STATE = 0
    stateChange = time.perf_counter()

    turnTime = 1.2
    prevTime = time.perf_counter()    

    restart = False
    restartTime = 5.0

    while True:
        curTime = time.perf_counter() - timeOffset

        # read sensors
        distanceLeft = read_sensor(0)
        distanceFront = read_sensor(1)
        distanceRight = read_sensor(2)
        distanceBack = 8191

        print(f"L:{distanceLeft} F:{distanceFront} R:{distanceRight} B:{distanceBack}")

        # line detection (camera)
        area = getArea(picam2,0)
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

                # milestones for behavior
                if numOfTurns == 4 or numOfTurns == 8:
                    restart = True
                elif(numOfTurns == 12):
                    line12 = curTime

                print(numOfTurns)

        # stop condition
        if numOfTurns >= 12:
            if curTime - line12 > timeToStop:
                break

        # restart sensors if needed
        if restart and curTime - lastLine > restartTime:
            restart = False
            restart_system()

        # skip loop if sensor invalid
        if -1 in [distanceLeft, distanceFront, distanceRight, distanceBack]:
            print("One or more sensors unavailable, retrying...")
            time.sleep(0.1)
            continue

        # PD control
        error = distFromWall - distanceLeft
        errDif = error-prevError
        angle = Kp*error + Kd*errDif

        # turning state timing
        if STATE == 1:
            if curTime - stateChange > turnTime:
                STATE = 0
                stateChange = curTime

        # steering logic
        if STATE == 0:
            if distanceLeft > 2000:
                SetAngle(0)
            else:
                SetAngle(angle)
        elif STATE == 1:
            SetAngle(45)

        forward(speed)

        prevError = error
        time.sleep(0.05)

        print("Time of loop: ",curTime - prevTime)
        prevTime = curTime

    stop()


# =========================
# SENSOR STARTUP
# =========================

# initialize sensors
for i, ch in enumerate(order):
    init_sensor(i, ch)
    time.sleep(0.2)

# button callback
button.when_pressed = pressed

# wait for button press
try:
    while True:
        time.sleep(0.1)
        
        if pressedStart:
            pressedStart = False

            try:
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
