from gpiozero import Button, Device
from gpiozero.pins.lgpio import LGPIOFactory

Device.pin_factory = LGPIOFactory()

button = Button(16, pull_up=True)

def pressed():
    print("Button press")

while True:
    button.when_pressed = pressed
