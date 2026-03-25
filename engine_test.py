import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

IN1 = 6
IN2 = 5
ENA = 13

GPIO.setup([IN1, IN2, ENA], GPIO.OUT)

pwmEngine = GPIO.PWM(ENA, 1000)
pwmEngine.start(0)

def reverse(x):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    pwmEngine.ChangeDutyCycle(x)

def forward(x):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    pwmEngine.ChangeDutyCycle(x)
    
while True:
    forward(77)  # 0-100 
