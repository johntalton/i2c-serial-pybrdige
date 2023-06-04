# import time
import board

from digitalio import DigitalInOut, Direction, Pull
import neopixel
import busio

import usb_cdc
import os
import asyncio

#
COLOR_Disconnected_1 = (250, 0, 50)
COLOR_Disconnected_2 = (125, 0, 50)
COLOR_NOOP = (10, 10, 100)
COLOR_Process_Line = (10, 255, 10)
COLOR_Unknown_Command = (100, 10, 100)
# COLOR_End_Of_Line = (0, 0, 0)
COLOR_Hazard = (255, 0, 255)

def tryBus0():
    try:
        return board.I2C()  # for i2c on board pins #0
    except Exception:
        print("tried and failed bus0")
        return None

def tryBus1():
    try:
        return board.STEMMA_I2C()  # for i2c on quic port #1
    except RuntimeError as re:
        print("tried and failed bus1", re)
        return None
    except Exception as e:
        print("tried and failed bus1", e)
        return None

def trySWBus(scl, sda):
    try:
        return busio.I2C(board.SCL1, board.SDA1)
    except Exception:
        return None


def getInfo():
    print(board.board_id)


def getEnabled(name):
    enableStr = os.getenv(name, "false")
    return enableStr.lower() == "true"

def getBrightness(defaultPercent=5):
    brightness = os.getenv("neo_brightness_percent", defaultPercent)
    return brightness / 100

status = {
    "CDC": None,
    "CMD": None
}

configuration = {
    "bus0": {"enabled": getEnabled("bus0"), "bus": None},
    "bus1": {"enabled": getEnabled("bus1"), "bus": None},
    "neo": {
        "brightness": getBrightness()
    }
}

if (configuration["bus0"]["enabled"]):
    # print("Enable bus0")
    configuration["bus0"]["bus"] = tryBus0()
    # if(configuration["bus0"]["bus"] == None):
    #   print("disabled bus0")
    #   configuration["bus0"]["enabled"] = False

if (configuration["bus1"]["enabled"]):
    # print("Enable bus1")
    configuration["bus1"]["bus"] = tryBus1()
    # if(configuration["bus1"]["bus"] == None):
    #   print("disabled bus1")
    #   configuration["bus1"]["enabled"] = False

print(configuration)

# npp = DigitalInOut(board.NEOPIXEL_POWER)
# npp.direction = Direction.OUTPUT
# npp.value = True

pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=configuration["neo"]["brightness"])

# button = DigitalInOut(board.BUTTON)
# button.direction = Direction.INPUT
# button.pull = Pull.DOWN

led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT
led.value = False

#
if(usb_cdc.data != None):
    usb_cdc.data.timeout = 0.25

    usb_cdc.data.reset_output_buffer()
    usb_cdc.data.reset_input_buffer()
    usb_cdc.data.flush()


def CDCCommandHandler_ReadReg(i2c):
    print("R - register read")
    buf = usb_cdc.data.read(3)
    if(len(buf) != 3):
        print(f"invalid buffer length {length}")
        status["CMD"] = "error"
        return

    addr7 = buf[0]
    register = buf[1]
    length = buf[2]

    print(f"read from {hex(addr7)} at register {hex(register)} for length {length}")

    while not i2c.try_lock():
        pass

    try:
        result = bytearray(length)
        i2c.writeto_then_readfrom(addr7, bytes([register]), result)
        # print(result)
        usb_cdc.data.write(result)

    finally:
        i2c.unlock()

def CDCCommandHandler_WriteReg(i2c):
    print("W - register write")
    buf = usb_cdc.data.read(3)
    if(len(buf) != 3):
        print(f"invalid buffer length {length}")
        status["CMD"] = "error"
        return

    addr7 = buf[0]
    register = buf[1]
    length = buf[2]
    buf = usb_cdc.data.read(length)

    print(f"write to {hex(addr7)} at register {hex(register)} for length {length}")

    buf = bytes([register]) + buf

    while not i2c.try_lock():
        pass

    try:
        i2c.writeto(addr7, buf)
    finally:
        i2c.unlock()

def CDCCommandHandler_Read(i2c):
    print("r - read")
    buf = usb_cdc.data.read(2)
    addr7 = buf[0]
    length = buf[1]

    print(f"read from{hex(addr7)} for length {length}")

    while not i2c.try_lock():
        pass

    try:
        result = bytearray(length)
        i2c.readfrom_into(addr7, result)
        # print(result)
        usb_cdc.data.write(result)

    finally:
        i2c.unlock()

def CDCCommandHandler_Write(i2c):
    print("w - write")
    buf = usb_cdc.data.read(2)
    addr7 = buf[0]
    length = buf[1]
    buf = usb_cdc.data.read(length)

    print(f"write to {hex(addr7)} for length {length}")

    while not i2c.try_lock():
        pass

    try:
        i2c.writeto(addr7, buf)
    finally:
        i2c.unlock()

def CDCCommandHandler_Scan(i2c):
    print("d - scan")
    while not i2c.try_lock():
        pass

    try:
        scanList = i2c.scan()
        # print(scanList)

        result = bytearray(112)

        for key in scanList:
            # print(f"set {key} to true")
            result[key - 0x8] = True

        # print(result)
        usb_cdc.data.write(result)

    finally:
        i2c.unlock()

async def CDCCommandHandler(status):
    while True:
        if usb_cdc.data == None:
            await asyncio.sleep(5)
            status["CDC"] = "disabled"
            continue

        if not usb_cdc.data.connected:
            status["CDC"] = "disconnected"
            await asyncio.sleep(2)
            continue

        status["CDC"] = "connected"

        line = usb_cdc.data.read(1)
        command = line[0] if len(line) > 0 else None
        if command == 0x00 or command == None:
            status["CMD"] = "NOOP"
            await asyncio.sleep(.25)
            continue

        status["CMD"] = chr(command)
        # print("not a noop", chr(command))

        if (chr(command) == "e"):
            print("e - echo byte")
            eb = usb_cdc.data.read(1)
            usb_cdc.data.write(eb)

        elif (chr(command) == "?"):
            print("? - status info")
            status = bytes([])

        elif (chr(command) == "d"):
            CDCCommandHandler_Scan(configuration["bus1"]["bus"])

        elif (chr(command) == "R"):
            CDCCommandHandler_ReadReg(configuration["bus1"]["bus"])

        elif (chr(command) == "W"):
            CDCCommandHandler_WriteReg(configuration["bus1"]["bus"])

        elif (chr(command) == "r"):
            CDCCommandHandler_Read(configuration["bus1"]["bus"])

        elif (chr(command) == "w"):
            CDCCommandHandler_Write(configuration["bus1"]["bus"])

        else:
            status["CMD"] = "unknown"

        await asyncio.sleep(.25)


async def NEOHandler():
    while True:
        # print("NEO Handlers", status)

        if(status["CDC"] is None):
            print("CDC Init")
            pixels.fill(COLOR_Hazard)
            await asyncio.sleep(2)

        elif (status["CDC"] == "disabled"):
            print("CDC Disabled")
            pixels.fill(COLOR_Hazard)
            await asyncio.sleep(1)

        elif (status["CDC"] == "disconnected"):
            print("CDC Disconnected")
            pixels.fill(COLOR_Disconnected_1)
            await asyncio.sleep(1)
            pixels.fill(COLOR_Disconnected_2)
            await asyncio.sleep(1)

        elif (status["CDC"] == "connected"):
            # print("led connected", status["CMD"])
            if (status["CMD"] == "NOOP"):
                pixels.fill(COLOR_NOOP)
                await asyncio.sleep(0.25)
            elif (status["CMD"] == "error"):
                pixels.fill(COLOR_Hazard)
                await asyncio.sleep(1)
            elif (status["CMD"] == "unknown"):
                pixels.fill(COLOR_Unknown_Command)
                await asyncio.sleep(1)
            else:
                pixels.fill(COLOR_Process_Line)
                await asyncio.sleep(1)

        else:
            print("CDC Status Unknown", status["CDC"])
            pixels.fill(COLOR_Hazard)
            await asyncio.sleep(3)

#
print("**********************")
loop = asyncio.get_event_loop()
loop.create_task(CDCCommandHandler(status))
loop.create_task(NEOHandler())
loop.run_forever()
print("End of Line")

