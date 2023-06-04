import usb_cdc
import storage

#storage.disable_usb_drive()
#usb_cdc.disable()
usb_cdc.enable(console=True, data=True)
print("enabled")
