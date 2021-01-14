import board
import busio
import digitalio
import asyncio
import adafruit_rgb_display.st7789 as st7789
from adafruit_rgb_display.rgb import color565

from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306


class Display:
    def __init__(self, servokit, conf):
        i2c = board.I2C()
        self.screen = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
        image = Image.new("1", (self.screen.width, self.screen.height))
        self.draw = ImageDraw.Draw(image)


    def display(self, image_data, x, y, x1, y1):
        self.screen._block(x, y, x1, y1, image_data)

    def image(self, image):
        #self.draw.image(image)
        self.screen.show()
    
    def clear(self):
        self.fill(0, 0, 0,self.screen.width,self.screen.height)

    def fill(self, color565, x, y, w, h):
        color = 255 if color565 > 0 else 0
        self.draw.rectangle((x, y, w, h), outline=color, fill=color)
        self.screen.show()

    def pixel(self, x, y, color565):
        color = 255 if color565 > 0 else 0
        return self.screen.pixel(x, y, color)

    def gif(self, gif, loop):
        #https://github.com/adafruit/Adafruit_CircuitPython_RGB_screen/blob/master/examples/rgb_screen_pillow_animated_gif.py
        raise NotImplementedError

    def backlight(self, *args):
        if not args:
            return 0
    @property
    def backlight_brightness(self):
        return 0

    @backlight_brightness.setter
    def backlight_brightness(self, value):
        return 0

class ST7789:
    def __init__(self, servokit, conf):
        self.screen_backlight = servokit.servo[conf['servo']['backlight']['channel']]
        self.screen_backlight.set_pulse_width_range(0, 100000//conf['servo']['freq'])
        self.servo_update_rate = conf['servo']['update_rate']

        self.screen_backlight.fraction = 0
        spi = board.SPI()
        cs_pin = digitalio.DigitalInOut(getattr(board, f'D{conf["screen"]["cs"]}'))
        dc_pin = digitalio.DigitalInOut(getattr(board, f'D{conf["screen"]["dc"]}'))
        reset_pin = digitalio.DigitalInOut(getattr(board, f'D{conf["screen"]["rst"]}'))
        self.screen = st7789.ST7789(spi, rotation=90, width=135, height=240, x_offset=53, y_offset=40,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=24000000,
        )

    def display(self, image_data, x, y, x1, y1):
        self.screen._block(x, y, x1, y1, image_data)

    def fill(self, color565, x, y, w, h):
        self.screen.fill_rectangle(x, y, w, h, color565)

    def pixel(self, x, y, color565):
        return self.screen.pixel(x, y, color565)

    def gif(self, gif, loop):
        #https://github.com/adafruit/Adafruit_CircuitPython_RGB_screen/blob/master/examples/rgb_screen_pillow_animated_gif.py
        raise NotImplementedError

    @property
    def backlight_brightness(self):
        return self.screen_backlight.fraction
    
    @backlight_brightness.setter
    def backlight_brightness(self, brightness):
        self.screen_backlight.fraction = brightness

    async def backlight(self, *args):
        if not args:
            return self.screen_backlight.fraction or 0
        value = args[0]
        duration = speed = None
        try:
            duration = args[1]
            speed = args[2]
        except IndexError:
            pass
        if not (duration or speed):
            self.backlight_brightness = value or 0
            return
        elif speed:
            if not 0 < speed <= 1 * self.servo_update_rate:
                raise ValueError(f'Speed must be 0 ~ {1*self.servo_update_rate}')
            duration = (value - self.screen_backlight.fraction)/speed
        steps = int(duration * self.servo_update_rate)
        interval = 1/self.servo_update_rate
        try:
            inc = (value-self.screen_backlight.fraction)/steps
            for _ in range(steps):
                await asyncio.sleep(interval)
                self.screen_backlight.fraction += inc
        except (ZeroDivisionError, ValueError):
            pass
        finally:
            self.backlight_brightness = value
