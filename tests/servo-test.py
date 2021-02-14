import board
import busio
import adafruit_pca9685
from adafruit_motor.servo import Servo,ContinuousServo

i2c = busio.I2C(board.SCL, board.SDA)
pca = adafruit_pca9685.PCA9685(i2c)
pca.frequency = 60
servos = (ContinuousServo(pca.channels[14]),ContinuousServo(pca.channels[15]))

def motor(id,mid,range,throttle):
   servo = servos[id]
   servo.set_pulse_width_range(mid-range, mid+range)
   servo.throttle = throttle

def drive(throttle):
   motor(0,1468,-100,throttle)
   motor(1,1468, 100,throttle)

drive(0.0)
