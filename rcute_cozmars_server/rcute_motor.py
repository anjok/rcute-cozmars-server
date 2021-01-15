import gpiozero
import adafruit_motor.servo

# wrappers around either servo controlled motors or gpiozero.Motor

class ServoMotor:
    def __init__(self, servokit, conf, key):
        self.conf = conf
        self.key = key
        self.channel = servokit.pca.channels[self.conf['channel']]
        print(f"motor_conf_{key}={conf}")
        self.motor = adafruit_motor.servo.ContinuousServo(self.channel, min_pulse=self.conf['min_pulse'], max_pulse=self.conf['max_pulse'])

    @property
    def value(self):
        return -self.motor.throttle

    @value.setter
    def value(self, value):
        print(f"motor_{self.key}={value:.03f}")
        self.motor.throttle = -value

    def close(self):
        self.motor.value = 0

class NormalMotor:
    def __init__(self, servokit, conf, key):
        self.motor = gpiozero.Motor(*conf['motor'][key])
   
    @property
    def value(self):
        return self.motor.value

    @value.setter
    def value(self, value):
        self.motor.value = value

    def close(self):
        self.motor.close()

class Motor:
    def __init__(self, servokit, conf, key):
        servo_conf = conf['servo'][key + '_motor']
        if servo_conf:
            self.motor = ServoMotor(servokit, servo_conf, key)
        else:
            self.motor = gpiozero.Motor(*conf['motor'][key])

    @property
    def value(self):
        return self.motor.value

    @value.setter
    def value(self, value):
        self.motor.value = value

    def close(self):
        self.motor.close()
