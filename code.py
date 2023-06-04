import time
import board
from digitalio import DigitalInOut, Direction, Pull
import neopixel
import busio
import usb_cdc

# i2c = board.I2C() # for i2c on board pins #0
# i2c = board.STEMMA_I2C() # for i2c on quic port #1
i2c = busio.I2C(board.SCL1, board.SDA1)

# tca = adafruit_tca9548a.TCA9548A(i2c)

pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

button = DigitalInOut(board.BUTTON)

usb_cdc.data.timeout = 1

while True:
    if(button.value == False):
        print("Button!")

    if not usb_cdc.data.connected:
        pixels.fill((25, 0, 0))
        time.sleep(1)
        pixels.fill((15, 0, 0))
        time.sleep(1)
        continue

    # print("await line")
    pixels.fill((10, 10, 85))
    line = usb_cdc.data.read(1)
    command = line[0] if len(line) > 0 else None
    if command == 0x00 or command == None:
        pixels.fill((10, 10, 55))
        time.sleep(0.25)
        continue

    pixels.fill((10, 55, 10))
    print(f"parse command {command}")

    next = usb_cdc.data.read(1)
    last = usb_cdc.data.read(1)

    usb_cdc.data.write(bytes([command]))
    usb_cdc.data.flush()
    # usb_cdc.data.reset_output_buffer()
    time.sleep(1)



    #while not i2c.try_lock():
    #    pass
    #try:
    #    result = bytearray(1)
    #    i2c.readfrom_into(0x70, result)
    #    print(result)
    #finally:
    #    i2c.unlock()
