import time
from gpiozero import PWMOutputDevice, DigitalOutputDevice, Servo, Device, Button
from gpiozero.pins.lgpio import LGPIOFactory

IN1 = 6
IN2 = 5
ENA = 13

Device.pin_factory = LGPIOFactory()
IN1_dev = DigitalOutputDevice(IN1)
IN2_dev = DigitalOutputDevice(IN2)
ENA_pwm = PWMOutputDevice(ENA, frequency=1000)

def forward(speed):
    IN1_dev.off()
    IN2_dev.on()
    ENA_pwm.value = speed / 100  # 0–100 → 0–1

def reverse(speed):
    IN1_dev.on()
    IN2_dev.off()
    ENA_pwm.value = speed / 100
    
while True:
    forward(70)  # 0-100 
    time.sleep(1.0)
    reverse(70)
    time.sleep(1.0)
