import asyncio, time
from collections import Iterable
from gpiozero import Motor, Button, LineSensor, DigitalOutputDevice#, TonalBuzzer, DistanceSensor
from .distance_sensor import DistanceSensor
from gpiozero.tones import Tone
from .rcute_servokit import ServoKit
from .rcute_screen import Screen
from .rcute_motor import Motor
from . import util

import json

from wsmprpc import RPCStream

class CozmarsServer:

    async def __aenter__(self):
        await self.lock.acquire()
        self.lmotor = Motor(self.servokit, self.conf, 'left')
        self.rmotor = Motor(self.servokit, self.conf, 'right')
        # self.reset_servos()
        self.reset_motors()
        self.lir = LineSensor(self.conf['ir']['left'], queue_len=3, sample_rate=10, pull_up=True)
        self.rir = LineSensor(self.conf['ir']['right'], queue_len=3, sample_rate=10, pull_up=True)
        sonar_cfg = self.conf['sonar']
        self.sonar = DistanceSensor(trigger=sonar_cfg['trigger'], echo=sonar_cfg['echo'], max_distance=sonar_cfg['max'], threshold_distance=sonar_cfg['threshold'], queue_len=5, partial=True)

        self._sensor_event_queue = None
        self._button_last_press_time = 0
        def cb(ev, obj, attr):
            return lambda: self._sensor_event_queue and self.event_loop.call_soon_threadsafe(self._sensor_event_queue.put_nowait, (ev, getattr(obj, attr)))
        def button_press_cb():
            if self._sensor_event_queue:
                now = time.time()
                if now - self._button_last_press_time <= self._double_press_max_interval:
                    ev = 'double_pressed'
                else:
                    ev = 'pressed'
                self.event_loop.call_soon_threadsafe(self._sensor_event_queue.put_nowait, (ev, True))
                self._button_last_press_time = now
        self.lir.when_line = self.lir.when_no_line = cb('lir', self.lir, 'value')
        self.rir.when_line = self.rir.when_no_line = cb('rir', self.rir, 'value')
        self.button.hold_time = 1
        self.button.when_pressed = button_press_cb
        self.button.when_released = cb('pressed', self.button, 'is_pressed')
        self.button.when_held = cb('held', self.button, 'is_held')
        self.sonar.when_in_range = cb('in_range', self.sonar, 'distance')
        self.sonar.when_out_of_range = cb('out_of_range', self.sonar, 'distance')
        self.screen.clear()
        self.screen.backlight_brightness = .05

        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.stop_all_motors()
        for a in [self.sonar, self.lir, self.rir, self.lmotor, self.rmotor, self.cam]:
            a and a.close()
        self.screen.backlight_brightness = None
        self.lock.release()

    def __del__(self):
        self.button.close()

    def __init__(self, conf_path=util.CONF, env_path=util.ENV):
        with open(conf_path) as cf:
            self.conf = json.load(cf)

        with open(env_path) as ef:
            self.env = json.load(ef)

        self.lock = asyncio.Lock()
        self.i2s_lock = asyncio.Lock()
        self.mic_int = False
        self.event_loop = asyncio.get_running_loop()

        self.button = Button(self.conf['button'])
        self.speaker_power = DigitalOutputDevice(self.conf['speaker'])
        self.cam = None

        self.servokit = ServoKit(channels=16, freq=self.conf['servo']['freq'])
        self.screen_backlight = self.servokit.servo[self.conf['servo']['backlight']['channel']]
        self.screen_backlight.set_pulse_width_range(0, 100000//self.conf['servo']['freq'])
        self.screen_backlight.fraction = 0
        spi = board.SPI()
        cs_pin = digitalio.DigitalInOut(getattr(board, f'D{self.conf["screen"]["cs"]}'))
        dc_pin = digitalio.DigitalInOut(getattr(board, f'D{self.conf["screen"]["dc"]}'))
        reset_pin = digitalio.DigitalInOut(getattr(board, f'D{self.conf["screen"]["rst"]}'))
        self.screen = st7789.ST7789(spi, rotation=90, width=135, height=240, x_offset=53, y_offset=40,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=24000000,
        )
        self.servo_update_rate = self.conf['servo']['update_rate']
        self._double_press_max_interval = .5
        self.reset_servos()
        self._head.angle = self.rarm.fraction = self.larm.fraction = 0
        time.sleep(.5)
        self.relax_lift()
        self.relax_head()

    @staticmethod
    def conf_servo(servokit, conf):
        servo = servokit.servos[conf['channel']]
        servo.set_pulse_width_range(conf['min_pulse'], conf['max_pulse'])
        return servo

    def reset_motors(self):
        self.motor_compensate = {'forward':list(self.conf['motor']['forward']), 'backward':list(self.conf['motor']['backward'])}

    def reset_servos(self):
        self.rarm = CozmarsServer.conf_servo(self.servokit, self.conf['servo']['right_arm'])
        self.larm = CozmarsServer.conf_servo(self.servokit, self.conf['servo']['left_arm'])
        self._head = CozmarsServer.conf_servo(self.servokit, self.conf['servo']['head'])
        self._head.set_actuation_range(-20, 20)

    def save_conf(self, conf_path=util.CONF):
        # only servo and motor configs are changed
        for servo_name, servo in zip(('right_arm', 'left_arm', 'head'), (self.rarm, self.larm, self._head)):
            self.conf['servo'][servo_name]['max_pulse'] = servo.max_pulse
            self.conf['servo'][servo_name]['min_pulse'] = servo.min_pulse
        for dir in ('forward', 'backward'):
            self.conf['motor'][dir] = list(self.motor_compensate[dir])
        with open(conf_path, 'w') as f:
            json.dump(self.conf, f, indent=2)

    def calibrate_motor(self, direction, left, right):
        self.motor_compensate[direction] = [left, right]

    def calibrate_servo(self, channel, min_pulse=None, max_pulse=None):
        '''
        for s in self.conf['servo'].values():
            if isinstance(s, dict) and s.get('channel')==channel:
                s['min_pulse'] = min_pulse
                s['max_pulse'] = max_pulse
        '''
        servo = self.servokit.servos[channel]
        servo.set_pulse_width_range(min_pulse or servo.min_pulse, max_pulse or servo.max_pulse)

    def get_env(self, name):
        return self.env[name]

    def set_env(self, name, value):
        self.env[name] = value

    def del_env(self, name):
        del self.env[name]

    def save_env(self, env_path=util.ENV):
        with open(env_path, 'w') as f:
            json.dump(self.env, f, indent=2)

    def motor_compensate_speed(self, speed, i):
        return self.motor_compensate['forward' if speed>0 else 'backward'][i]

    def motor_adjust_speed(self, speed, inverse):
        min_value = self.motor_min_value
        actual_min_value = (min_value if speed>0 else -min_value)
        if inverse:
            return (speed-(actual_min_value))/(1.0 - min_value) if speed else 0
        return speed*(1-min_value) + actual_min_value if speed else 0

    def real_speed_motor(self, sp):
        '''
        1. compensate for speed inbalance of two motors
        2. the motors won't run when speed is lower than .2,
            so we map speed from (0, 1] => (.2, 1], (0, -1] => (-.2, -1] and 0 => 0
        '''
        out = [0,0]
        for i, s in enumerate(sp):
            s = s if s < 1 else 1
            s if s > -1 else -1
            s = s*self.motor_compensate_speed(s, i)
            s = self.motor_adjust_speed(s,False) if s else 0
            out[i] = s
        return out

    def mapped_single_speed(self, speed, i):
        # real speed -> mapped speed
        # if abs(speed)) < .2 too small, remap
        adjusted = self.motor_adjust_speed(speed, True)
        comp = self.motor_compensate_speed(adjusted, i)
        res = max(-1, min(1, adjusted/comp))
        return res

    def mapped_speed_motor(self, sp):
        # real speed -> mapped speed
        if not isinstance(sp, Iterable):
            sp = [sp, sp]
        return list((self.mapped_single_speed(s,i)) for i, s in enumerate(sp))

    def mapped_speed(self, sp):
        # real speed -> mapped speed
        if not isinstance(sp, Iterable):
            sp = [sp, sp]
        return list(s - self.offsets[i] for i, s in enumerate(sp))

    def real_speed(self, sp):
        '''
        1. compensate for speed inbalance of two motors
        2. the motors won't run when speed is lower than .2,
            so we map speed from (0, 1] => (.2, 1], (0, -1] => (-.2, -1] and 0 => 0
        '''
        out = [0,0]
        for i, s in enumerate(sp):
            # left motor is a bit off
            s = s + self.offsets[i]
            s = s if s < 1 else 1
            s if s > -1 else -1
            out[i] = s
        return out

    async def speed(self, speed=None, duration=None):
        self.offsets = [-0.1, 0]
        self.motor_min_value=0.0

        if speed is None:
            return self.mapped_speed((self.lmotor.value, self.rmotor.value))
        print(f"iter={isinstance(speed, Iterable)} list={isinstance(speed, list)} ")
        if isinstance(speed, Iterable):
            speed = [speed[0], speed[1]]
        else:
            speed = [speed, speed]       
        print(f"current={(self.lmotor.value, self.rmotor.value)} should={speed} duration={duration}")
        print(f"wanted={self.real_speed(speed)}")
        print(f"inverse={self.mapped_speed(speed)}")
        speed = self.real_speed(speed)
        def set(motor,speed):
            motor.value = speed
            return True
        done = [False,False]
        if set(self.lmotor,speed[0]):
            done[0] = True
        if set(self.rmotor,speed[1]):
            done[1] = True
        print(f"raw={(self.lmotor.value, self.rmotor.value)} should={done}")
        if duration:
            await asyncio.sleep(duration)
            print(f"off after={duration}")
            #set(self.lmotor, 0)
            #set(self.rmotor, 0)
            await self.speed(0)

    async def speed_(self, speed, duration=None):
        if speed is None:
            return self.mapped_speed((self.lmotor.value, self.rmotor.value))
        print(f"current={(self.lmotor.value, self.rmotor.value)} should={self.mapped_speed(speed)}")
        speed = self.real_speed(speed)
        def set_(motor,speed):
            inc = speed - motor.value
            if 0 < abs(inc) < .3:
                motor.value = speed
                return True
            elif inc:
                motor.value += .3 if inc > 0 else -.3
            return False
        def set_(motor,speed):
            motor.value = speed
            return True
        done = [False,False]
        while (True,True) != done:
            print(f"current={(self.lmotor.value, self.rmotor.value)} should={done}")
            if set(self.lmotor,speed[0]):
                done[0] = True
            if set(self.rmotor,speed[1]):
                done[1] = True
            await asyncio.sleep(.05)
        if duration:
            await asyncio.sleep(duration)
            await self.speed((0, 0))

    def stop_all_motors(self):
        self.lmotor.value = self.rmotor.value = 0
        self.relax_lift()
        self.relax_head()

    async def backlight(self, *args):
        self.screen.backlight(args)

    def relax_lift(self):
        self.larm.relax()
        self.rarm.relax()

    def relax_head(self):
        self._head.relax()

    async def lift(self, *args):
        if not args:
            return self.rarm.fraction
        height = args[0]
        if height == None:
            self.rarm.fraction = self.larm.fraction = height
            return
        if not 0<= height <= 1:
            raise ValueError('Height must be 0 to 1')
        duration = speed = None
        try:
            duration = args[1]
            speed = args[2]
        except IndexError:
            pass
        if not (self.rarm.fraction!=None and (speed or duration)):
            self.rarm.fraction = height
            self.larm.fraction = height
            return
        elif speed:
            if not 0 < speed <= 1 * self.servo_update_rate:
                raise ValueError(f'Speed must be 0 ~ {1*self.servo_update_rate}')
            duration = abs(height - self.larm.fraction)/speed
        if duration == 0:
            return
        steps = int(duration * self.servo_update_rate)
        interval = 1/self.servo_update_rate
        try:
            inc = (height-self.larm.fraction)/steps
            for _ in range(steps):
                await asyncio.sleep(interval)
                self.larm.fraction += inc
                self.rarm.fraction += inc
        except (ZeroDivisionError, ValueError):
            pass
        finally:
            self.rarm.fraction = height
            self.larm.fraction = height

    async def head(self, *args):
        if not args:
            return self._head.angle
        angle = args[0]
        if angle == None:
            self._head.angle = None
            return
        if not -20 <= angle <= 20:
            raise ValueError('Angle must be -20 ~ 20')
        duration = speed = None
        try:
            duration = args[1]
            speed = args[2]
        except IndexError:
            pass
        if not (self._head.angle!=None and (speed or duration)):
            self._head.angle = angle
            return
        elif speed:
            if not 0 < speed <= 80 * self.servo_update_rate:
                raise ValueError(f'Speed must be 0 ~ {80*self.servo_update_rate}')
            duration = abs(angle - self._head.angle)/speed
        steps = int(duration*self.servo_update_rate)
        interval = 1/self.servo_update_rate
        try:
            inc = (angle-self._head.angle)/steps
            for _ in range(steps):
                await asyncio.sleep(interval)
                self._head.angle += inc
        except (ZeroDivisionError, ValueError):
            pass
        finally:
            self._head.angle = angle

    def display(self, image_data, x, y, x1, y1):
        self.screen.display(image_data, x, y, x1, y1)

    def fill(self, color565, x, y, w, h):
        self.screen.fill(color565, x, y, w, h)

    def pixel(self, color565, x, y):
        return self.screen.pixel(x, y, color565)

    # def gif(self, gif, loop):
    #     #https://github.com/adafruit/Adafruit_CircuitPython_RGB_screen/blob/master/examples/rgb_screen_pillow_animated_gif.py
    #     raise NotImplemented

    # async def play(self, *, request_stream):
    #     async for freq in request_stream:
    #         self.buzzer.play(Tone.from_frequency(freq)) if freq else self.buzzer.stop()

    # async def tone(self, freq, duration=None):
    #     self.buzzer.play(Tone.from_frequency(freq)) if freq else self.buzzer.stop()
    #     if duration:
    #         await asyncio.sleep(duration)
    #         self.buzzer.stop()

    async def sensor_data(self, update_rate=None):
        timeout = 1/update_rate if update_rate else None
        try:
            # if the below queue has a max size, it'd better be a `RPCStream` instead of `asyncio.Queue`,
            # and call `force_put_nowait` instead of `put_nowait` in `loop.call_soon_threadsafe`,
            # otherwise if the queue if full,
            # an `asyncio.QueueFull` exception will be raised inside the main loop!
            self._sensor_event_queue = asyncio.Queue()
            yield 'lir', self.lir.value
            yield 'rir', self.rir.value
            while True:
                try:
                    yield await asyncio.wait_for(self._sensor_event_queue.get(), timeout)
                except asyncio.TimeoutError:
                    yield 'sonar', self.sonar.distance
        except Exception as e:
            self._sensor_event_queue = None
            raise e

    def double_press_max_interval(self, *args):
        if args:
            self._double_press_max_interval = args[0]
        else:
            return self._double_press_max_interval

    def hold_repeat(self, *args):
        if args:
            self.button.hold_repeat = args[0]
        else:
            return self.button.hold_repeat

    def hold_time(self, *args):
        if args:
            self.button.hold_time = args[0]
        else:
            return self.button.hold_time

    def threshold_distance(self, *args):
        if args:
            self.sonar.threshold_distance = args[0]
        else:
            return self.sonar.threshold_distance

    def max_distance(self, *args):
        if args:
            self.sonar.max_distance = args[0]
        else:
            return self.sonar.max_distance

    def distance(self):
        return self.sonar.distance

    def _volume(self, control, value):
        from subprocess import check_output
        if value:
            check_output(f'amixer set {control} {value}%'.split(' '))
        else:
            a = check_output(f'amixer get {control}'.split(' '))
            return int(a[a.index(b'[') + 1 : a.index(b'%')])

    def microphone_volume(self, value=None):
        return self._volume('Boost', value)

    def speaker_volume(self, value=None):
        return self._volume('PCM', value)

    async def capture(self, options):
        import picamera, io
        if self.cam is None or self.cam.closed:
            self.cam = picamera.PiCamera()
            self.cam.vflip = self.cam.hflip = True
        delay = options.pop('delay', 0)
        standby = options.pop('standby', False)
        try:
            buf = io.BytesIO()
            delay and await asyncio.sleep(delay)
            self.cam.capture(buf, **options)
            buf.seek(0)
            return buf.read()
        finally:
            not standby and self.cam.close()

    async def camera(self, width, height, framerate):
        import picamera, io, threading
        try:
            queue = RPCStream(2)
            stop_ev = threading.Event()

            def bg_run(loop):
                nonlocal queue, stop_ev, width, height, framerate
                with picamera.PiCamera(resolution=(width, height), framerate=framerate) as cam:
                    # Camera warm-up time
                    time.sleep(2)
                    stream = io.BytesIO()
                    for _ in cam.capture_continuous(stream, 'jpeg', use_video_port=True):
                        if stop_ev.isSet():
                            break
                        stream.truncate()
                        stream.seek(0)
                        loop.call_soon_threadsafe(queue.force_put_nowait, stream.read())
                        # queue.put_nowait(stream.read())
                        stream.seek(0)

            loop = asyncio.get_running_loop()
            # threading.Thread(target=bg_run, args=[loop]).start()
            bg_task = loop.run_in_executor(None, bg_run, loop)

            while True:
                yield await queue.get()

        finally:
            stop_ev.set()
            await bg_task


    async def speaker(self, samplerate, dtype, blocksize, *, request_stream):
        import sounddevice as sd
        loop = asyncio.get_running_loop()
        done_ev = asyncio.Event()

        def fcb():
            self.mic_int = False
            self.speaker_power.off()
            loop.call_soon_threadsafe(done_ev.set)

        zeros = None
        def cb(outdata, frames, time, status): # don't do time consuming await/future.result() in this callback
            nonlocal zeros
            # if status:
            #     print('[speaker]', status)
                # loop.call_soon_threadsafe(done_ev.set)
                # raise sd.CallbackAbort
            if request_stream.empty():
                if not zeros:
                    zeros = b'\x00' * len(outdata)
                outdata[:] = zeros
            else:
                b = request_stream.get_nowait() # is get_nowait thread safe?
                if isinstance(b, StopAsyncIteration):
                    raise sd.CallbackStop
                else:
                    outdata[:] = b

        while request_stream.empty():
            await asyncio.sleep(.1)

        self.mic_int = True
        async with self.i2s_lock:
            self.speaker_power.on()
            with sd.RawOutputStream(callback=cb, dtype=dtype, samplerate=samplerate, channels=1, blocksize=blocksize, finished_callback=fcb):
                await done_ev.wait()


    async def microphone(self, samplerate, dtype, blocksize):
        import sounddevice as sd
        loop = asyncio.get_running_loop()
        queue = RPCStream(2)
        def cb(indata, frames, time, status):
            # if status:
            #     print('[mic]', status)
                # raise sd.CallbackAbort
            loop.call_soon_threadsafe(queue.force_put_nowait, bytes(indata))

        while True:
            async with self.i2s_lock:
                with sd.RawInputStream(callback=cb, samplerate=samplerate, blocksize=blocksize, channels=1, dtype=dtype):
                    while not self.mic_int:
                        yield await queue.get()
            await asyncio.sleep(.01)

