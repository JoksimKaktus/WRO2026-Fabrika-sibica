import time
import board
import busio
import adafruit_vl53l0x
import adafruit_tca9548a
from smbus2 import SMBus
from mpu6050 import mpu6050


MUX_ADDR = 0x70
MUX_CHANNEL_3 = 0x08
I2C_BUS = 1
MPU_ADDR = 0x68

def select_mux_channel_3():
    with SMBus(I2C_BUS) as bus:
        bus.write_byte(MUX_ADDR, MUX_CHANNEL_3)
        time.sleep(0.01)

def disable_mux():
    with SMBus(I2C_BUS) as bus:
        bus.write_byte(MUX_ADDR, 0x00)
        time.sleep(0.01)


i2c = busio.I2C(board.SCL, board.SDA)
tca = adafruit_tca9548a.TCA9548A(i2c, address=0x70)

sensors=[adafruit_vl53l0x.VL53L0X(tca[0]),adafruit_vl53l0x.VL53L0X(tca[1]),adafruit_vl53l0x.VL53L0X(tca[4]),adafruit_vl53l0x.VL53L0X(tca[2])]

select_mux_channel_3()
sensor = mpu6050(MPU_ADDR)

try:
    while True:
        # Sensors
        distance = [sensors[i].range for i in range(4)]

        print(f"Distance Left: {distance[0]} mm")
        print(f"Distance Front: {distance[1]} mm")
        print(f"Distance Right: {distance[2]} mm")
        print(f"Distance Back: {distance[3]} mm")

        print("-------------------------------")

        # Gyroscope
        select_mux_channel_3()

        accel_data = sensor.get_accel_data()
        gyro_data = sensor.get_gyro_data()
        temp = sensor.get_temp()

        print("Accelerometer data")
        print("x:", accel_data["x"])
        print("y:", accel_data["y"])
        print("z:", accel_data["z"])

        print("Gyroscope data")
        print("x:", gyro_data["x"])
        print("y:", gyro_data["y"])
        print("z:", gyro_data["z"])

        print("Temp:", temp, "C")
        print("-" * 30)

        #time.sleep(0.5)
except KeyboardInterrupt:
    print("Exiting...")
finally:
    disable_mux()