##########################################
# MLX90640 Thermal Camera w Raspberry Pi
# Uses Pimoroni Display Hat Mini for display and button control
##########################################
#
import math
import time, board, busio
import numpy as np
import adafruit_mlx90640
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from displayhatmini import DisplayHATMini
import sys

i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)  # setup I2C
mlx = adafruit_mlx90640.MLX90640(i2c)  # begin MLX90640 with I2C comm
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_16_HZ  # set refresh rate
mlx_shape = (24, 32)  # mlx90640 shape

mlx_interp_val = 10  # interpolate # on each dimension
frame = np.zeros(mlx_shape[0] * mlx_shape[1])  # 768 pts

width = DisplayHATMini.WIDTH
height = DisplayHATMini.HEIGHT
buffer = Image.new("RGB", (width, height))
draw = ImageDraw.Draw(buffer)

displayhatmini = DisplayHATMini(buffer)
displayhatmini.set_led(0.05, 0.05, 0.05)

# Load default font.
font = ImageFont.load_default()

# initial settings
max_temp = 50
min_temp = 0


# Taken from https://github.com/pimoroni/st7789-python/blob/master/examples/shapes.py (Thank you Pimoroni)
# Define a function to create rotated text.  Unfortunately PIL doesn't have good
# native support for rotated fonts, but this function can be used to make a
# text image and rotate it so it's easy to paste in the buffer.
def draw_rotated_text(image, text, position, angle, font, fill=(255, 255, 255)):
    # Get rendered font width and height.
    draw = ImageDraw.Draw(image)
    width, height = draw.textsize(text, font=font)
    # Create a new image with transparent background to store the text.
    textimage = Image.new('RGBA', (width, height), (0, 255, 0, 0))
    # Render the text.
    textdraw = ImageDraw.Draw(textimage)
    textdraw.text((0, 0), text, font=font, fill=fill)
    # Rotate the text image.
    rotated = textimage.rotate(angle, expand=1)
    # Paste the text into the image, using it as a mask for transparency.
    image.paste(rotated, position, rotated)


def get_color_for_temp(degrees):
    temp = int(math.trunc(math.ceil(degrees)))
    red_value = 255 / (max_temp - min_temp) * (temp - min_temp)
    blue_value = 255 / (max_temp - min_temp) * (max_temp - temp)
    return int(math.trunc(red_value)), 0, int(math.trunc(blue_value))


def draw_plot():
    mlx.getFrame(frame)  # read mlx90640
    data_array = np.reshape(frame, mlx_shape)  # remap arrange to two x & y array

    # NOTE: The X Axis is designed to allow for the Sensor being opposite to the screen
    #       so if the sensor is facing the same direction as the screen i.e. 'Selfie mode'
    #       then X Axis could be drawn on the far side of the screen and worked backwards
    x = 0
    draw_x = 0
    while x < len(data_array):
        y = 0
        draw_y = 0
        while y < len(data_array[x]):
            color_temp = get_color_for_temp(data_array[x][y])
            draw.rectangle((draw_x, draw_y, draw_x + 10, draw_y + 10),
                           fill=(color_temp[0], color_temp[1], color_temp[2]))
            y = y + 1
            draw_y = y * 10

        x = x + 1
        draw_x = x * 10

    # Write buffer to display hardware, must be called to make things visible on the display!
    displayhatmini.display()
    return


def draw_range():
    elements = np.linspace(max_temp, 0, 10)
    start_x = 290
    end_x = 310
    start_y = 15
    box_size = 20

    draw.rectangle((265, 15, end_x, start_y + (box_size * len(elements))), fill=(0, 0, 0))
    draw_rotated_text(buffer, str(max_temp), (265, 15), 0, font, fill=(255, 255, 255))

    for element in elements:
        draw.rectangle((start_x, start_y, end_x, start_y + box_size), fill=(get_color_for_temp(element)))
        start_y = start_y + box_size

    start_y = start_y - int(box_size / 2)
    draw_rotated_text(buffer, str(min_temp), (265, start_y), 0, font, fill=(255, 255, 255))

    displayhatmini.display()


update_full_display = True
display_debug = False
t_array = []
while True:
    t1 = time.monotonic()  # for determining frame rate
    try:
        draw_plot()  # update plot
    except:
        continue

    if display_debug:
        t_array.append(time.monotonic() - t1)
        if len(t_array) > 10:
            t_array = t_array[1:]  # recent times for frame rate approx
        draw.rectangle((260, 0, 320, 240), fill=(0, 0, 0))
        draw_rotated_text(buffer, 'Frame Rate: {0:2.1f}fps'.format(len(t_array) / np.sum(t_array)), (0, 0), 0, font,
                          fill=(255, 255, 255))

    if update_full_display:
        draw_range()
        update_full_display = False
        displayhatmini.set_led(0.5, 0, 0)

    if displayhatmini.read_button(displayhatmini.BUTTON_X):
        sys.exit(0)
    elif displayhatmini.read_button(displayhatmini.BUTTON_A):
        if max_temp < 100:
            max_temp = max_temp + 10
            draw_range()
    elif displayhatmini.read_button(displayhatmini.BUTTON_B):
        if max_temp > 20:
            max_temp = max_temp - 10
            draw_range()
    elif displayhatmini.read_button(displayhatmini.BUTTON_Y):
        if display_debug:
            display_debug = True
        else:
            display_debug = False

    time.sleep(0.001)
