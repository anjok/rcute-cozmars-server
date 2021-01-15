import board
import busio
import digitalio
from PIL import Image, ImageDraw, ImageFont
 # Use for I2C.
i2c = board.I2C()
import adafruit_ssd1306
screen = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

screen.fill(0)
screen.show()


BORDER = 5
image = Image.new("1", (screen.width, screen.height))
draw = ImageDraw.Draw(image)
draw.rectangle((0, 0, screen.width, screen.height), outline=255, fill=255)
draw.rectangle(
    (BORDER, BORDER, screen.width - BORDER - 1, screen.height - BORDER - 1),
    outline=0,
    fill=0,
)
font = ImageFont.load_default()
text = "Hello World!"
(font_width, font_height) = font.getsize(text)
draw.text(
    (screen.width // 2 - font_width // 2, screen.height // 2 - font_height // 2),
    text,
    font=font,
    fill=255,
)
 
screen.image(image)
screen.show()