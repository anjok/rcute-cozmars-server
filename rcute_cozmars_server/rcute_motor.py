import gpiozero
from .cozmars_server import CozmarsServer

class Motor:
    def __init__(self, servokit, conf, key):
        self.conf = conf['servo'][key + 'motor']
        self.max = self.conf['max']
        self.min = self.conf['min']
        self.motor = CozmarsServer.conf_servo(servokit, self.conf)
        # channel = conf['motor'][key]['servo']
        # self.motor = gpiozero.Motor(*conf['motor'][key])

    def close(self):
        self.motor.close()

    @property
    def value(self):
        angle = self.motor.angle
        return (angle - self.min)/(self.max - self.min)

    @value.setter
    def value(self, value):
        angle = self.min + (self.max - self.min) * value
        self.motor.angle = angle

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
