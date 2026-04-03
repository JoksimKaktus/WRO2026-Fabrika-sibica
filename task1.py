import time
import math
import board
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

pressedStart = False
lastAngle = 0

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
servo = AngularServo(
    SERVO_PIN,
    min_angle=-90,
    max_angle=90,
    min_pulse_width=0.0005,   # 1 ms
    max_pulse_width=0.0025,   # 2 ms
    frame_width=0.02    
    )
button = Button(16, pull_up=True)

xshuts = [DigitalOutputDevice(pin) for pin in XSHUT_PINS]

# Slower I2C = much more stable
i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
tca = adafruit_tca9548a.TCA9548A(i2c, address=MUX_ADDR)

# sensor index -> mux channel
order = [0, 1, 4, 2]
sensors = [None] * 4

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()


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
    ENA_pwm.value = speed / 100


def reverse(speed): # speed 0-100
    IN1_dev.on()
    IN2_dev.off()
    ENA_pwm.value = speed / 100


def stop(): 
    ENA_pwm.value = 0
    servo.value = 0
    print("STOPPED")

def cleanup():
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


def SetAngle(angle): # from -1 to 1, -1 - left, 0 - straight, 1 - right
    global lastAngle, targetAngle
    angle = max(angle,-45)
    angle = min(angle, 45)
    if abs(lastAngle - angle) < 2:
        return
    servo.angle = angle
    lastAngle = angle


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

    # Sensor missing -> try once to recreate it
    if sensors[index] is None:
        try:
            xshuts[index].off()
            time.sleep(0.05)
            xshuts[index].on()
            time.sleep(0.05)

            sensors[index] = adafruit_vl53l0x.VL53L0X(tca[channel])
            sensors[index].measurement_timing_budget = 33000

        except Exception as e:
            print(f"Sensor {index} init failed: {e}")
            sensors[index] = None
            return -1

    try:
        # Normal fast read
        ret = sensors[index].range
        time.sleep(0.01)
        return ret

    except Exception as e:
        print(f"Sensor {index} read failed: {e}")

        # Throw away broken object
        sensors[index] = None

        try:
            # Quick reset and reinit
            xshuts[index].off()
            time.sleep(0.05)
            xshuts[index].on()
            time.sleep(0.05)

            sensors[index] = adafruit_vl53l0x.VL53L0X(tca[channel])
            sensors[index].measurement_timing_budget = 33000

            return sensors[index].range

        except Exception as e2:
            print(f"Sensor {index} recovery failed: {e2}")
            sensors[index] = None
            return -1

def restart_system():
    global sensors, servo, order

    stop()
    time.sleep(0.2)

    # Reset sensors
    for i, ch in enumerate(order):
        sensors[i] = None
        init_sensor(i, ch)

    # Recreate servo object
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

    speed = 30
    slowSpeed = 30
    distFromWall = 300
    distFromFront = 0
    Kp = 0.08
    Kd = 0.4
    prevError = 0

    numOfTurns = 0
    corner = False
    lastLine = time.perf_counter()
    line12 = 0
    timeToStop = 6.0


    # 0 - clockwise
    # 1 - counter clockwise
    # robot didnt figure out yet
    direction = 1

    # 0 - Normal, wall following
    # 1 - Turning
    # 2 - Go straight
    STATE = 0
    stateChange = time.perf_counter()

    turnTime = 2.3
    prevTime = time.perf_counter()    

    restart = False
    restartTime = 7.0


    while True:
        curTime = time.perf_counter()

        area = getArea(picam2)
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
                if numOfTurns == 4 or numOfTurns == 8:
                    restart = True
                elif(numOfTurns == 12):
                    line12 = curTime
                print(numOfTurns)

        if numOfTurns >= 12:
            if curTime - line12 > timeToStop:
                break

        if restart and curTime - lastLine > restartTime:
            restart = False
            restart_system()

        if STATE == 2:
            if curTime - stateChange < turnTime:
                SetAngle(-45)
                continue

        distanceLeft = read_sensor(0)
        distanceFront = read_sensor(1)
        distanceRight = read_sensor(2)
        distanceBack = read_sensor(3)

        print(
            f"L:{distanceLeft} "
            f"F:{distanceFront} "
            f"R:{distanceRight} "
            f"B:{distanceBack}"
        )

        # select_mux_channel_3()
        # gyro_data = gyro.get_gyro_data()
        # xRot = gyro_data["x"]+2.65   # adding average error when stationary

        # Skip this loop if one of the sensors failed
        if -1 in [distanceLeft, distanceFront, distanceRight, distanceBack]:
            print("One or more sensors unavailable, retrying...")
            time.sleep(0.1)
            continue

        if direction == 2:
            if distanceRight > 2000:
                direction = 0
            elif distanceLeft > 2000:
                direction = 1

        error = 0
        if direction == 1:
            error = -distFromWall + distanceRight
        elif direction == 0:
            error = distFromWall - distanceLeft

        errDif = error-prevError
        angle = Kp*error + Kd*errDif

        if STATE == 0:
            #if curTime - stateChange < 3.0:
                #dontchange
             if distFromFront > distanceFront:
                 STATE = 1
                 stateChange = curTime
        elif STATE == 1:
            if curTime - stateChange > turnTime:
                STATE = 0
                stateChange = curTime
        elif STATE == 2:
            STATE = 1
            stateChange = curTime
        


        if STATE == 0:
            if distanceRight > 2000:
                SetAngle(0)
            else:
                SetAngle(angle)
        elif STATE == 1:
            if direction == 0:
                SetAngle(45)
            else:
                SetAngle(-45)
        else:
            SetAngle(0)

        forward(speed)

        
        prevError = error
        time.sleep(0.01)
        print("Time of loop: ",curTime - prevTime)
        prevTime = curTime

    stop()

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
