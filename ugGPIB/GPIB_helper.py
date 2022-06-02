# -*- coding: utf-8 -*-
import errno
import usb.core
from usb.core import USBError
from usb.util import find_descriptor


def _device_matcher(device):
    # Make sure that a "Vendor Specific" interface is found in the configuration
    # bInterfaceClass    0xFF
    # bInterfaceSubClass 0xFF
    # bInterfaceProtocol 0xFF
    for cfg in device:
        if (find_descriptor(cfg, bInterfaceClass=0xFF) is not None
            and find_descriptor(cfg, bInterfaceSubClass=0xFF) is not None
            and find_descriptor(cfg, bInterfaceProtocol=0xFF) is not None):
            return True


def get_usb_devices(vendor=0x04d8, product=0x000c):
    # Search for all USB Devices
    # 0x04d8 is the Microchip USB manufacturer ID
    # 0x000c is the specific product id assigned

    # Returns a generator
    return usb.core.find(
           idVendor=vendor,
           idProduct=product,
           custom_match=_device_matcher,
           find_all=True,
    )


def get_usb_endpoints(device):
    device_config = device.get_active_configuration()
    if device_config is None:
        # Only set a new configuration if the device has not been previously been set up,
        # because this would trigger a reset of the USB state
        device.set_configuration()
        device_config = device.get_active_configuration()

    # Get the first interface
    interface = device_config[(0, 0)]

    # Get read and write endpoints
    read_ep = find_descriptor(
        interface,
        # Match the first IN endpoint
        custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
    )

    write_ep = find_descriptor(
        interface,
        # Match the first OUT endpoint
        custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
    )

    # Flush the read_ep (fingers crossed, that this is not some other device, that we are not interested in)
    try:
        while True:
            read_ep.read(64, timeout=1)
    except USBError as e:
        if e.errno == errno.ETIMEDOUT:
            # There is nothing to read, so we can carry on
            pass
        else:
            raise

    return read_ep, write_ep
