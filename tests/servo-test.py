import board
import busio
import adafruit_pca9685
from adafruit_motor.servo import Servo
i2c = busio.I2C(board.SCL, board.SDA)
pca = adafruit_pca9685.PCA9685(i2c)
pca.frequency = 50
servo = Servo(pca.channels[1])
servo.set_pulse_width_range(1000, 2000)
servo.angle = 90
