import board
import busio
import digitalio
import asyncio

import adafruit_rgb_display
import adafruit_rgb_display.st7789 as st7789
from adafruit_rgb_display.rgb import color565

from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

class OledScreen:
    def __init__(self, servokit, conf):
        i2c = board.I2C()
        self.screen = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
        self.image = Image.new("1", (self.screen.width, self.screen.height))
        self.draw = ImageDraw.Draw(self.image)

    def display(self, image_data, x, y, x1, y1):
        class numpy_holder(object):
            pass
        def createMatrix(rowCount, colCount, dataList):   
            mat = []
            for i in range (rowCount):
                rowList = []
                for j in range (colCount):
                    if dataList[j] not in mat:
                        rowList.append(1 if dataList[j] else 0)
                mat.append(rowList)
            #holder = numpy_holder()
            mat.__array_interface__ = {"shape":[colCount, rowCount]}
            return mat 

        cols = x1-x
        rows = y1-y
        arr = createMatrix(rows, cols, image_data)
        image = Image.fromarray(arr)
        print(f"image pos={x}, {y}, {x1}, {y1} data={image_data}")
        self.show_image(x, y, x1, y1, image)

    def show_image(self, image):
        self.screen.image(image.convert("1").resize((self.screen.width, self.screen.height)))
        self.screen.show()

    def image(self, image):
        self.show_image(image)

    def show(self):
        self.show_image(self.image)
    
    def clear(self):
        self.fill(0, 0, 0,self.screen.width,self.screen.height)

    def fill(self, color565, x, y, w, h):
        color = 255 if color565 > 0 else 0
        self.draw.rectangle((x, y, w, h), outline=color, fill=color)
        self.show()

    def pixel(self, x, y, color565):
        color = 255 if color565 > 0 else 0
        return self.screen.pixel(x, y, color)

    @property
    def backlight_brightness(self):
        return self._backlight_brightness

    @backlight_brightness.setter
    def backlight_brightness(self, value):
        self._backlight_brightness = value

class ST7789Screen:
    def __init__(self, servokit, conf):
        self.screen_backlight = servokit.servos[conf['servo']['backlight']['channel']]
        self.screen_backlight.set_pulse_width_range(0, 100000//conf['servo']['freq'])
        self.servo_update_rate = conf['servo']['update_rate']
        self.screen_backlight.fraction = 0
        spi = board.SPI()
        cs_pin = digitalio.DigitalInOut(getattr(board, f'D{conf["screen"]["cs"]}'))
        dc_pin = digitalio.DigitalInOut(getattr(board, f'D{conf["screen"]["dc"]}'))
        reset_pin = digitalio.DigitalInOut(getattr(board, f'D{conf["screen"]["rst"]}'))
        self.screen = adafruit_rgb_display.st7789.ST7789(spi, rotation=90, width=135, height=240, x_offset=53, y_offset=40,
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

    def image(self, image):
        self.screen.image(image)

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

class Screen:
    def __init__(self, servokit, conf):
        if conf['screen']['type'] == 'oled':
            self.screen = OledScreen(servokit, conf)
        else:
            self.screen = ST7789Screen(conf)

    def display(self, image_data, x, y, x1, y1):
        self.screen.display(image_data, x, y, x1, y1)

    @property
    def width(self):
        return self.screen.screen.width

    @property
    def height(self):
        return self.screen.screen.height

    def clear(self):
        self.fill(0, 0, 0, self.width, self.height)
    def clear(self):
        self.fill(0, 0, 0, self.screen.width, self.screen.height)

    def image(self, image):
        self.screen.show_image(image)

    def fill(self, color565, x, y, w, h):
        self.screen.fill(color565, x, y, w, h)

    def pixel(self, x, y, color565):
        return self.screen.pixel(x, y, color565)

    def gif(self, gif, loop):
        #https://github.com/adafruit/Adafruit_CircuitPython_RGB_screen/blob/master/examples/rgb_screen_pillow_animated_gif.py
        raise NotImplementedError

    def backlight(self, *args):
        if not args:
            return 0

    @property
    def backlight_brightness(self):
        return self.screen.backlight_brightness

    @backlight_brightness.setter
    def backlight_brightness(self, value):
        self.screen.backlight_brightness = value
