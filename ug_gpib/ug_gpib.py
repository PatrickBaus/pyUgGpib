# -*- coding: utf-8 -*-

from array import array
import binascii
from enum import IntEnum
import errno
import logging
import time
from usb.core import USBError

from .gpib_helper import get_usb_devices, get_usb_endpoints


class UgPlusCommands(IntEnum):
    """Internal commands used by the UGPlus"""
    GET_FIRMWARE_VERSION = 0x00
    GET_SERIES = 0x0E
    RESET = 0x0F
    WRITE = 0x32
    READ = 0x33
    DISCOVER_GPIB_DEVICES = 0x34
    GET_MANUFACTURER_ID = 0xFE


class UGPlusGpib:
    @property
    def logger(self):
        return self.__logger

    def __init__(self, device_series=2654079, timeout=None):
        self.__timeout = timeout
        self.__logger = logging.getLogger(__name__)
        # Search for the right GPIB device
        # This is a pain in the b***, because the USB iSerialNumber is always 0x00
        # So we will iterate over all possible PIC18 controllers and query them.
        # Note: this might break other stuff, if devices that match our search criterion
        # do not like to be talked to.

        self.logger.info("Enumerating GPIB USB devices")
        self.read_ep, self.write_ep = None, None
        for device in get_usb_devices():
            self.read_ep, self.write_ep = get_usb_endpoints(device)

            # Initialize usb read buffer
            self.__usb_read_buf = array('B', [])

            # Now query the device
            _, series = self.get_series_number()
            self.logger.info("Device found: Series number %(series)s", {"series": series})

            if series == device_series:
                self.logger.info("Connecting to device %(series)s", {"series": series})
                # Get the firmware version to apply bug fixes on the fly
                self.__firmware_version = self.get_firmware_version()
                break

            del self.read_ep
            del self.write_ep

        # No device found
        if self.read_ep is None:
            raise ValueError('GPIB Adapter not found')

    # Read byte(s) from USB endpoint
    # datalen - Number of bytes to read
    # Returns a byte array
    def usb_read(self, datalen=1):
        # Read USB in 64 byte chunks, store bytes until empty, then read again
        self.logger.debug(
            "Trying to read %(datalen)s bytes from adapter. Number of bytes in buffer. %(size_of_buffer)s",
            {"datalen": datalen, "size_of_buffer": len(self.__usb_read_buf)}
        )
        while len(self.__usb_read_buf) < datalen:
            bytes_to_read = self.read_ep.wMaxPacketSize
            self.logger.debug("Reading %(no_bytes)s bytes from USB device", {"no_bytes": bytes_to_read})
            self.__usb_read_buf += self.read_ep.read(size_or_buffer=bytes_to_read, timeout=self.__timeout)

        self.logger.debug(
            "USB Read buffer: %(buffer)s, size: %(size_of_buffer)s",
            {"buffer": self.__usb_read_buf, "size_of_buffer": len(self.__usb_read_buf)}
        )
        # Retrieve the requested number of bytes, then remove the items
        data = self.__usb_read_buf[0:datalen]
        del self.__usb_read_buf[0:datalen]

        return data

    # Write UGSimple command
    # address - internal command address
    # data    - List of byte width data
    def __device_write(self, command, data=None):
        assert isinstance(command, UgPlusCommands)
        if data is None:
            data = []
        # Prepare packet for writing (add GPIB address and the size of the final packet)
        packet = [command, len(data) + 2]

        packet.extend(data)
        self.logger.debug("Package sent to adapter: %(data)s", {"data": packet})

        # Send packet via usb
        self.write_ep.write(packet, self.__timeout)

    def __device_read(self, command_expected):
        assert isinstance(command_expected, UgPlusCommands)
        # Read a single byte to see if a valid command has been received
        command = self.usb_read()[0]
        try:
            command = UgPlusCommands(command)
        except ValueError:
            pass

        if command != command_expected:
            self.logger.error(
                "Command '%(command)s' does not match expected command '%(expected_command)r\nBytestream received",
                {"command": command, "expected_command": command_expected}
            )
            return None

        self.logger.debug("Got reply to command %(command)s", {"command": command})

        # Valid command, read next byte to determine length of command
        length = self.usb_read()[0]
        self.logger.debug("Size of reply: %(length)s", {"length": length})

        # Handle firmware quirks
        # **********************
        if self.__firmware_version == (1, 0):
            if command == UgPlusCommands.GET_MANUFACTURER_ID:
                # BUG: The GET_MANUFACTURER_ID command returns an extra byte in UGPlus Firmware 1.0, possibly
                # an out-of-bounds read!
                self.logger.debug(
                    "Patching bug in GET_MANUFACTURER_ID command. Increasing length of packet from %(length)s to %(new_length)s bytes",
                    {"length": length, "new_length": length+1}
                )
                length += 1
            elif command == UgPlusCommands.DISCOVER_GPIB_DEVICES:
                # BUG: The DISCOVER_GPIB_DEVICES command returns an extra byte in UGPlus Firmware 1.0, possibly an
                # out-of-bounds read!
                self.logger.debug(
                    "Patching bug in DISCOVER_GPIB_DEVICES command. Increasing length of packet from %(length)s to %(new_length)s bytes",
                    {"length": length, "new_length": length+1}
                )
                length += 1
            elif command == UgPlusCommands.READ:
                # BUG: The READ command returns 2 more bytes if the read returns an empty string. This is an error code
                # (1st byte is either 0x01 or 0x0A) and likely an out-of-bounds read.
                # The last of the byte depends on the previous payload! It is the same as the third byte of the previous
                # payload
                if length < 5:
                    # Note: if length == 3, there is no device connected. if length == 4, there is nothing to read.
                    # Probably...
                    self.logger.debug(
                        "Patching bug in READ command. Increasing length of packet from %(length)s to %(new_length)s bytes",
                        {"length": length, "new_length": 5}
                    )
                    length = 5
        # **********************

        # Read the rest of the byte_data, the command and packet length field are included the length (hence -2)
        byte_data = self.usb_read(length - 2)

        self.logger.debug(
            "Received packet:\n  Header:\n    Command: %(command)r\n    Length %(length)d\n  Payload:\n    %(payload)s",
            {"command": command, "length": length, "payload": [hex(i) for i in byte_data]}
        )

        return byte_data

    def __device_query(self, command):
        self.__device_write(command)
        return self.__device_read(command)

    # Get the manufacturer id
    # Returns manufacturer id string
    def get_manufacturer_id(self):
        byte_data = self.__device_query(UgPlusCommands.GET_MANUFACTURER_ID)
        if self.__firmware_version == (1, 0):
            # BUG: strip the last byte
            byte_data = byte_data[:-1]

        return ''.join([chr(x) for x in byte_data])

    # Get the series number
    # Returns the series number
    # MMFFFFFF - e.g. 011e7f7f (Model 0x01, Function 0x1e7f7f)
    # MM       - Model number
    # FFFFFF   - Function number
    def get_series_number(self):
        model, *series = self.__device_query(UgPlusCommands.GET_SERIES)

        return model, int.from_bytes(series, byteorder='big')

    # Get the firmware version
    # Returns a (major, minor) tuple
    def get_firmware_version(self):
        return tuple(self.__device_query(UgPlusCommands.GET_FIRMWARE_VERSION))

    # Query Devices connected to UGSimple
    def get_gpib_devices(self):
        # XXX Not sure what the last byte is for
        # Zero devices 0x0A
        # One device  0x1E
        # Two devices 0x7F
        # Stripping for now
        devices = self.__device_query(UgPlusCommands.DISCOVER_GPIB_DEVICES)[:-1]
#        self.get_firmware_version()

        # Handle firmware quirks
        # **********************
        if self.__firmware_version == (1, 0):
            devices = devices[:-1]
        return tuple(devices)

    def reset(self):
        self.logger.info("Resetting GPIB adapter")
        self.__device_write(UgPlusCommands.RESET)

    # Write to GPIB Address
    # address - GPIB Address
    # data    - Data to write to address
    def write(self, address, data=None):
        payload = bytearray([address, 0x0F]) + bytearray(data, "ascii")

        # Send write command (no return)
        self.__device_write(UgPlusCommands.WRITE, payload)

    # Read from GPIB Address
    # address - GPIB Address
    # Returns a byte array
    def read(self, address, delay=0):
        # Prepare read request command
        payload = bytearray([address, 0x0F])
#        payload = bytearray([address, ])

        # Request read
        self.__device_write(UgPlusCommands.READ, payload)

        # Delay if necessary
        time.sleep(delay)

        # Read data sent from GPIB device
        try:
            byte_data = self.__device_read(UgPlusCommands.READ)
        except USBError as exc:
            if exc.errno == errno.ETIMEDOUT:
                self.logger.error("Reading from device timed out")
                return None
            raise

        if byte_data is None:
            return None

        # Strip the next two bytes, because the actual payload is prepended by a header containing the GPIB device ID
        # and a delimiter
        # addr = byte_data[0]
        success = byte_data[1] != 0x0A

        self.logger.debug("Final USB Read buffer: %(buffer)s", {"buffer": self.__usb_read_buf})

        if not success:
            if len(self.__usb_read_buf) > 0:
                self.logger.debug("Clearing USB Read buffer")
                self.__usb_read_buf = array('B', [])    # clear usb read buffer
            raise OSError(
                errno.EIO,
                f"I/O error: Cannot read from GPIB device at address {address}. Is the device attached?"
            )

        byte_data = byte_data[2:]

        # Strip final linefeed
        # byte_data = byte_data[:-1]

        # Convert to an ascii byte array
        byte_data = binascii.b2a_qp(byte_data)

        return byte_data
