"""
Helper functions supporting the UGPlusGpib library.
"""
import errno
from typing import Generator

import usb.core
from usb.core import USBError
from usb.util import find_descriptor


def _device_matcher(device: usb.core.Device) -> bool:
    """
    Returns `True` if a device matches our description.
    Parameters
    ----------
    device: usb.core.Device
        The device to test
    Returns
    -------
    bool
        True if the device matches
    """
    # Check for a "Vendor Specific" interface with the following properties
    # bInterfaceClass    0xFF
    # bInterfaceSubClass 0xFF
    # bInterfaceProtocol 0xFF
    for cfg in device:
        if (
            find_descriptor(cfg, bInterfaceClass=0xFF) is not None
            and find_descriptor(cfg, bInterfaceSubClass=0xFF) is not None
            and find_descriptor(cfg, bInterfaceProtocol=0xFF) is not None
        ):
            return True
    return False


def get_usb_devices(vendor_id: int = 0x04D8, product_id: int = 0x000C) -> Generator[usb.core.Device, None, None]:
    """
    Search for USB devices, that match the vendor id and product id. The default vendor_id is Microchip, which is used
    by at least some devices.
    Parameters
    ----------
    vendor_id: int, default=0x04d8
        The usb vendor id
    product_id: int, default=0x000c
        The usb product id
    Yields
    -------
    usb.Device
        Returns a generator of the devices found
    """
    return usb.core.find(
        idVendor=vendor_id,
        idProduct=product_id,
        custom_match=_device_matcher,
        find_all=True,
    )


def get_usb_endpoints(device: usb.core.Device) -> tuple[usb.core.Endpoint, usb.core.Endpoint]:
    """
    Get the read and write endpoint for a given device
    Parameters
    ----------
    device: usb.core.Device
        The device to extract the endpoints from
    Returns
    -------
    tuple of usb.core.Endpoint
        The read and write endpoint
    """
    device_config = device.get_active_configuration()
    if device_config is None:
        # Only set a new configuration if the device has not been previously been set up,
        # because this would trigger a reset of the USB state
        device.set_configuration()
        device_config = device.get_active_configuration()

    # Get the first interface
    interface = device_config[(0, 0)]

    # Get read and write endpoints
    read_ep: usb.core.Endpoint
    read_ep = find_descriptor(
        interface,
        # Match the first IN endpoint
        custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN,
    )

    write_ep: usb.core.Endpoint
    write_ep = find_descriptor(
        interface,
        # Match the first OUT endpoint
        custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT,
    )

    # Flush the read_ep (fingers crossed, that this is not some other device, that we are not interested in)
    try:
        while True:
            read_ep.read(64, timeout=1)
    except USBError as exc:
        if exc.errno == errno.ETIMEDOUT:
            # There is nothing to read, so we can carry on
            pass
        else:
            raise

    return read_ep, write_ep
