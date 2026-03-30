import time
from gpiozero import PWMOutputDevice, DigitalOutputDevice, Servo, Device
from gpiozero.pins.lgpio import LGPIOFactory

Device.pin_factory = LGPIOFactory()
servo_pin = 19

servo_pwm = PWMOutputDevice(servo_pin, frequency=50)

def SetAngle(angle):
    pulse_ms = 1.5 + (angle * 0.5)

    # 50Hz = 20ms period
    duty_cycle = pulse_ms / 20.0

    servo_pwm.value = duty_cycle  # from -1 to +1

val = 0.9
while True:
    SetAngle(0.9)
    time.sleep(1.5)
    SetAngle(-0.9)
    time.sleep(1.5)
