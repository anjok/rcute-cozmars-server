import gpiozero
import adafruit_motor.servo

# wrappers around either servo controlled motors or gpiozero.Motor

class ServoMotor:
    def __init__(self, servokit, conf):
        self.conf = conf
        self.channel = servokit.pca.channels[self.conf['channel']]
        self.motor = adafruit_motor.servo.ContinuousServo(*self.conf)

    def close(self):
        self.motor.close()

    @property
    def value(self):
        return self.motor.throttle

    @value.setter
    def value(self, value):
        self.motor.throttle = value

class NormalMotor:
    def __init__(self, servokit, conf, key):
        self.motor = gpiozero.Motor(*conf['motor'][key])

    def close(self):
        self.motor.close()
    
    @property
    def value(self):
        return self.motor.value

    @value.setter
    def value(self, value):
        self.motor.value = value

class Motor:
    def __init__(self, servokit, conf, key):
        servo_conf = conf['servo'][key + '_motor']
        if servo_conf:
            self.motor = ServoMotor(servokit, servo_conf)
        else:
            self.motor = gpiozero.Motor(*conf['motor'][key])

    def close(self):
        self.motor.close()

    @property
    def value(self):
        return self.motor.angle

    @value.setter
    def value(self, value):
        self.motor.value = value
