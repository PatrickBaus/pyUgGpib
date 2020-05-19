#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2015 by Jacob Alexander
#
# This file is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This file is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this file.  If not, see <http://www.gnu.org/licenses/>.

### Imports ###

from array import array
import binascii
from enum import IntEnum
import errno
import logging
import time
from usb.core import USBError

from .GPIB_helper import get_usb_devices, get_usb_endpoints

### Constants ###

# Internal commands used by the UGPlus
class ugplus_commands(IntEnum):
    GET_FIRMWARE_VERSION = 0x00
    GET_SERIAL = 0x0E
    RESET = 0x0F
    WRITE = 0x32
    READ = 0x33
    DISCOVER_GPIB_DEVICES = 0x34
    GET_MANUFACTURER_ID = 0xFE

### Classes ###

class UGPlusGPIB:
    @property
    def logger(self):
        return self.__logger

    def __init__(self, device_serial=None, timeout=None):
        self.timeout = timeout
        self.__logger = logging.getLogger(__name__)
        # Search for the right GPIB device
        # This is a pain in the b***, because the USB iSerialNumber is always 0x00
        # So we will iterate over all possible PIC18 controllers and query them.
        # Note: this might break other stuff, if device that match our search criterion
        # do not like to be talked to.

        self.logger.info("Enumerating GPIB USB devices")
        for device in get_usb_devices():
#            self.logger.debug(device)
            self.read_ep, self.write_ep = get_usb_endpoints(device)

            # Initialize usb read buffer
            self.usb_read_buf = array('B', [])

            # Now query the device
            model, serial = self.get_serial_number()
            self.logger.info("Device found: Serial number %(serial)s", {"serial": serial})

            if device_serial is None or serial==device_serial:
                self.logger.info("Connecting to device %(serial)s", {"serial": serial})
                # Get the firmware version to apply bug fixes on the fly
                self.__firmware_version = self.get_firmware_version()
                break
            else:
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
        self.logger.debug("Trying to read %(datalen)s bytes from adapter. Number of bytes in buffer. %(size_of_buffer)s", {"datalen": datalen, "size_of_buffer": len(self.usb_read_buf)})
        while len(self.usb_read_buf) < datalen:
            bytes_to_read = self.read_ep.wMaxPacketSize
            self.logger.debug("Reading %(no_bytes)s bytes from USB device", {"no_bytes": bytes_to_read})
            self.usb_read_buf += self.read_ep.read(size_or_buffer=bytes_to_read, timeout=self.timeout)

        self.logger.debug("USB Read buffer: %(buffer)s, size: %(size_of_buffer)s", {"buffer": self.usb_read_buf, "size_of_buffer": len(self.usb_read_buf)})
        # Retrieve the requested number of bytes, then remove the items
        data = self.usb_read_buf[0:datalen]
        del self.usb_read_buf[0:datalen]

        return data

    # Write UGSimple command
    # address - internal command address
    # data    - List of byte width data
    def __device_write(self, command, data=[]):
        assert isinstance(command, ugplus_commands)
        # Prepare packet for writing (add GPIB address and the size of the final packet)
#        packet = [command, 6] if command == ugplus_commands.GET_FIRMWARE_VERSION else [command, len(data) + 2]
        packet = [command, len(data) + 2]

        packet.extend(data)
        self.logger.debug("Package sent to adapter: %(data)s", {"data": packet})

        # Send packet via usb
        self.write_ep.write(packet, self.timeout)

    def __device_read(self, command_expected):
        assert isinstance(command_expected, ugplus_commands)
        # Read a single byte to see if a valid command has been received
        command = self.usb_read()[0]
        try:
            command = ugplus_commands(command)
        except ValueError:
            pass

        if command != command_expected:
            self.logger.error("Command '%(command)s' does not match expected command '%(expected_command)r\nBytestream received", {"command": command, "expected_command": command_expected})
            return None
        else:
            self.logger.debug("Got reply to command %(command)s", {"command": command})

        # Valid command, read next byte to determine length of command
        length = self.usb_read()[0]
        self.logger.debug("Size of reply: %(length)s", {"length": length})

        # Handle firmware quirks
        # **********************
        if command == ugplus_commands.GET_MANUFACTURER_ID and self.__firmware_version == (1,0):
            # BUG: The GET_MANUFACTURER_ID command returns an extra byte in UGPlus Firmware 1.0, possibly out of bounds read!
            self.logger.debug("Patching bug in GET_MANUFACTURER_ID command. Increasing length of packet from %(length)s to %(new_length)s bytes", {"length": length, "new_length": length +1})
            length = length + 1
        if command == ugplus_commands.DISCOVER_GPIB_DEVICES and self.__firmware_version == (1,0):
            # BUG: The DISCOVER_GPIB_DEVICES command returns an extra byte in UGPlus Firmware 1.0, possibly out of bounds read!
            self.logger.debug("Patching bug in GET_MANUFACTURER_ID command. Increasing length of packet from %(length)s to %(new_length)s bytes", {"length": length, "new_length": length +1})
            length = length + 1
        if command == ugplus_commands.READ and self.__firmware_version == (1,0):
            # BUG: The READ command returns 5 bytes if the GPIB buffer is empty
            if length == 3:
                self.logger.debug("Patching bug in READ command. Increasing length of packet from %(length)s to 5 bytes", {"length": length})
                length = 5
        # **********************

        # Read the rest of the byteData, the command and packet length field are included the length (hence -2)
        self.logger.debug("Size of reply: %(length)s", {"length": length})
        byteData = self.usb_read(length - 2)

        self.logger.debug("Received packet:\n  Header:\n    Command: %(command)r\n    Length %(length)d\n  Payload:\n    %(payload)s", {"command": command, "length": length, "payload": [hex(i) for i in byteData]})

        return byteData

    def __device_query(self, command):
        self.__device_write(command)
        return self.__device_read(command)

    # Get the manufacturer id
    # Returns manufacturer id string
    def get_manufacturer_id(self):
        byte_data = self.__device_query(ugplus_commands.GET_MANUFACTURER_ID)
        if self.__firmware_version == (1,0):
            # BUG: strip the last byte
            byte_data = byte_data[:-1]

        return ''.join([chr(x) for x in byte_data])

    # Get the series number
    # Returns the series number
    # MMFFFFFF - e.g. 011e7f7f (Model 0x01, Function 0x1e7f7f)
    # MM       - Model number
    # FFFFFF   - Function number
    def get_serial_number(self):
        model, *serial = self.__device_query(ugplus_commands.GET_SERIAL)

        return model, int.from_bytes(serial, byteorder='big')

    # Get the firmware version
    # Returns a (major, minor) tuple
    def get_firmware_version(self):
        return tuple(self.__device_query(ugplus_commands.GET_FIRMWARE_VERSION))

    # Query Devices connected to UGSimple
    def get_gpib_devices(self):
        # XXX Not sure what the last byte is for
        # Zero devices 0x0A
        # One device  0x1E
        # Two devices 0x7F
        # Stripping for now
        devices = self.__device_query(ugplus_commands.DISCOVER_GPIB_DEVICES)[:-1]
        self.get_firmware_version()

        # Handle firmware quirks
        # **********************
        if self.__firmware_version == (1,0):
            devices = devices[:-1]
        return tuple(devices)

    def reset(self):
        self.logger.info("Resetting GPIB adapter")
        self.__device_write(ugplus_commands.RESET)

    # Write to GPIB Address
    # address - GPIB Address
    # data    - Data to write to address
    def write(self, address, data=None):
        # Prepare data with appended carriage-return and linefeed (CR + LF)
        payload = bytearray([address, 0x0F]) + bytearray(data, "ascii") + bytearray(b"\r\n")

        # Send write command (no return)
        self.__device_write(ugplus_commands.WRITE, payload)

    # Read from GPIB Address
    # address - GPIB Address
    # Returns a byte array
    def read(self, address, delay=0):
         # Prepare read request command
        payload = bytearray([address, 0x0F])

        # Request read
        self.__device_write(ugplus_commands.READ, payload)

        # Delay if necessary
        time.sleep(delay)

        # Read data sent from GPIB device
        try:
            byteData = self.__device_read(ugplus_commands.READ)
        except USBError as e:
            if e.errno == errno.ETIMEDOUT:
                self.logger.error("Reading from device timed out")
                return None
            else:
                raise

        # Strip the next two bytes, because the actual payload is prepended by a header containing the GPIB device ID and a delimiter
        byteData = byteData[2:]

        if byteData is None:
            return None

        # Strip final linefeed
#        byteData = byteData[:-1]

        # Convert to an ascii byte array
        byteData = binascii.b2a_qp(byteData)

        self.logger.debug("Final USB Read buffer: %(buffer)s", {"buffer": self.usb_read_buf})

        return byteData
