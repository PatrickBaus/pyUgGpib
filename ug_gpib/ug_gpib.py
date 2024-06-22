"""
A pure Python module for the LQ Electronics Corp UGPlus USB to GPIB Controller using pyUSB.
"""

from __future__ import annotations

import errno
import logging
import time
from enum import IntEnum
from typing import cast

from usb.core import Endpoint, USBError

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
    """A device driver for the LQ Electronics Corp UGPlus USB to GPIB Controller"""

    def __init__(self, device_series: int = 2654079, timeout: float | None = None) -> None:
        """
        Create a UGPlus device driver object.
        Parameters
        ----------
        device_series: int, optional
            The device series number to connect to
        timeout: float, optional
            The timeout for running commands in seconds
        """
        self.__timeout = timeout * 1000 if timeout is not None else None
        self.__firmware_version = None
        self.__logger = logging.getLogger(__name__)
        # Search for the right GPIB device
        # This is a pain in the b***, because the USB iSerialNumber is always 0x00
        # So we will iterate over all possible PIC18 controllers and query them.
        # Note: this might break other stuff, if devices that match our search criterion
        # do not like to be talked to.

        self.__logger.debug("Enumerating GPIB USB devices.")
        self.read_ep: Endpoint | None
        self.write_ep: Endpoint | None
        self.read_ep, self.write_ep = None, None
        for device in get_usb_devices():
            self.read_ep, self.write_ep = get_usb_endpoints(device)

            # Initialize usb read buffer
            self.__usb_read_buf = bytearray()

            # Now query the device, we can safely run this command, because there are no known firmware bugs so far
            _, series = self.get_series_number()
            self.__logger.info("Device found: Series number %(series)s.", {"series": series})

            if series == device_series:
                self.__logger.info("Connecting to device %(series)s.", {"series": series})
                # Get the firmware version to apply bug fixes on the fly. This command is also safe to run, because
                # there are no known firmware bugs.
                self.__firmware_version = self.version()
                break

            self.read_ep = None
            self.write_ep = None

        # No device found
        if self.read_ep is None:
            raise ValueError("GPIB Adapter not found.")

    def _usb_read(self, length: int = 1) -> bytes:
        """
        Read bytes from USB endpoint.
        Parameters
        ----------
        length: int
            The number of bytes to read
        Returns
        -------
        bytes
            The bytes read
        """
        assert self.read_ep is not None
        # Read USB in 64 byte chunks, store bytes until empty, then read again
        self.__logger.debug(
            "Trying to read %(length)s bytes from adapter. Number of bytes in buffer. %(size_of_buffer)s.",
            {"length": length, "size_of_buffer": len(self.__usb_read_buf)},
        )
        while len(self.__usb_read_buf) < length:
            bytes_to_read = self.read_ep.wMaxPacketSize
            self.__logger.debug("Reading %(no_bytes)s bytes from USB device.", {"no_bytes": bytes_to_read})
            self.__usb_read_buf += self.read_ep.read(size_or_buffer=bytes_to_read, timeout=self.__timeout)

        self.__logger.debug(
            "USB read buffer: %(buffer)s, size: %(size_of_buffer)s.",
            {"buffer": self.__usb_read_buf, "size_of_buffer": len(self.__usb_read_buf)},
        )
        # Retrieve the requested number of bytes, then remove them from the buffer
        data = bytes(self.__usb_read_buf[0:length])
        del self.__usb_read_buf[0:length]

        return data

    def __device_write(self, command: UgPlusCommands, data: bytes | None = None) -> None:
        """
        Write a command and data to the device
        Parameters
        ----------
        command: UgPlusCommands
            The command for the GPIB adapter
        data: bytes, optional
            The data to send along with the command. This is optional.
        """
        assert isinstance(command, UgPlusCommands)
        assert self.write_ep is not None
        if data is None:
            data = b""
        # Prepare packet for writing (add GPIB address and the size of the final packet)
        packet = [command, len(data) + 2]

        packet.extend(data)
        self.__logger.debug("Package sent to adapter: %(data)s.", {"data": packet})

        # Send packet via usb
        self.write_ep.write(packet, self.__timeout)

    def __device_read(self, command_expected: UgPlusCommands) -> bytes | None:
        """
        Read data from the GPIB adapter
        Parameters
        ----------
        command_expected: UgPlusCommands
            The command we expect to read. We need to know, because the adapter might return garbage.

        Returns
        -------
        bytes or None:
            Either return the bytes read or None, if there was an error.
        """
        assert isinstance(command_expected, UgPlusCommands)
        # Read a single byte to see if a valid command has been received
        command = self._usb_read()[0]
        try:
            command = UgPlusCommands(command)
        except ValueError:
            # We will handle that later
            pass

        if command != command_expected:
            self.__logger.error(
                "Command '%(command)s' does not match expected command '%(expected_command)r.\nBytestream received.",
                {"command": command, "expected_command": command_expected},
            )
            return None

        self.__logger.debug("Got reply to command %(command)s.", {"command": command})

        # Valid command, read next byte to determine length of command
        length = self._usb_read()[0]
        self.__logger.debug("Size of reply: %(length)s.", {"length": length})

        # Handle firmware quirks
        # **********************
        if self.__firmware_version == (1, 0):
            if command == UgPlusCommands.GET_MANUFACTURER_ID:
                # BUG: The GET_MANUFACTURER_ID command returns an extra byte in UGPlus Firmware 1.0, possibly
                # an out-of-bounds read!
                self.__logger.debug(
                    "Patching bug in GET_MANUFACTURER_ID command."
                    " Increasing length of packet from %(length)s to %(new_length)s bytes.",
                    {"length": length, "new_length": length + 1},
                )
                length += 1
            elif command == UgPlusCommands.DISCOVER_GPIB_DEVICES:
                # BUG: The DISCOVER_GPIB_DEVICES command returns an extra byte in UGPlus Firmware 1.0, possibly an
                # out-of-bounds read!
                self.__logger.debug(
                    "Patching bug in DISCOVER_GPIB_DEVICES command."
                    " Increasing length of packet from %(length)s to %(new_length)s bytes.",
                    {"length": length, "new_length": length + 1},
                )
                length += 1
            elif command == UgPlusCommands.READ:
                # BUG: The READ command returns 2 more bytes if the read returns an empty string. This is an error code
                # (1st byte is either 0x01 or 0x0A) and likely an out-of-bounds read.
                # The last of the bytes depends on the previous payload! It is the same as the third byte of the
                # previous payload.
                if length < 5:
                    # Note: if length == 3, there is no device connected. if length == 4, there is nothing to read.
                    # Probably...
                    self.__logger.debug(
                        "Patching bug in READ command."
                        " Increasing length of packet from %(length)s to %(new_length)s bytes.",
                        {"length": length, "new_length": 5},
                    )
                    length = 5
        # **********************

        # Read the rest of the byte_data, the command and packet length field are included the length (hence -2)
        byte_data = self._usb_read(length - 2)

        self.__logger.debug(
            "Received packet:\n  Header:\n    Command: %(command)r\n    Length %(length)d\n  Payload:"
            "\n    %(payload)s.",
            {"command": command, "length": length, "payload": [hex(i) for i in byte_data]},
        )

        return byte_data

    def _device_query(self, command: UgPlusCommands) -> bytes | None:
        """
        Query the GPIB controller. Write a command, then read back the answer immediately.
        Parameters
        ----------
        command

        Returns
        -------
        bytes or None:
            Either return the bytes read or None, if there was an error.
        """
        self.__device_write(command)
        return self.__device_read(command)

    def get_manufacturer_id(self) -> str:
        """
        Get the manufacturer id of the GPIB adapter.
        Returns
        -------
        str
            The manufacturer id
        """
        byte_data = self._device_query(UgPlusCommands.GET_MANUFACTURER_ID)
        if byte_data is None:
            raise ValueError("No reply received from GPIB adapter.")
        if self.__firmware_version == (1, 0):
            # BUG: strip the last byte
            byte_data = byte_data[:-1]

        return "".join([chr(x) for x in byte_data])

    def get_series_number(self) -> tuple[int, int]:
        """
        Query the GPIB controller series number(?). It does not seem to have a serial number.
        Returns
        -------
        tuple of int
            An integer that is the model number and an integer for the series number
        """
        byte_data = self._device_query(UgPlusCommands.GET_SERIES)
        if byte_data is None:
            raise ValueError("No reply received from GPIB adapter.")
        model, *series = byte_data

        return int(model), int.from_bytes(series, byteorder="big")

    def version(self) -> tuple[int, int]:
        """
        Get the GPIB adapter firmware version
        Returns
        -------
        tuple of int
            The major and minor firmware revision
        """
        byte_data = self._device_query(UgPlusCommands.GET_FIRMWARE_VERSION)
        if byte_data is None:
            raise ValueError("No reply received from GPIB adapter.")
        result = tuple(byte_data)
        assert len(result) == 2
        result = cast(tuple[int, int], result)
        return result

    def get_gpib_devices(self) -> tuple[int, ...]:
        """
        Try to identify all addresses, that have a GPIB device connected to it
        Returns
        -------
        tuple of int
            The primary addresses of the GPIB devices discovered
        """
        # Not sure what the last byte is for, maybe another out of bounds read
        # Zero devices 0x0A
        # One device  0x1E
        # Two devices 0x7F
        # Stripping for now
        byte_data = self._device_query(UgPlusCommands.DISCOVER_GPIB_DEVICES)
        if byte_data is None:
            raise ValueError("No reply received from GPIB adapter.")
        devices = byte_data[:-1]

        # Handle firmware quirks
        # **********************
        if self.__firmware_version == (1, 0):
            devices = devices[:-1]
        return tuple(devices)

    def reset(self):
        """Reset the controller."""
        self.__logger.info("Resetting GPIB adapter.")
        self.__device_write(UgPlusCommands.RESET)

    def write(self, pad: int, data: bytes) -> None:
        """
        Write data to the device at pad.
        Parameters
        ----------
        pad: int
            The primary address of the device
        data: bytes
            The data to send to the device.
        Returns
        -------

        """
        payload = bytes([pad, 0x0F]) + data

        # Send write command (no return)
        self.__device_write(UgPlusCommands.WRITE, payload)

    def read(self, pad: int, delay: float = 0) -> bytes | None:
        """
        Read from the device at pad (primary gpib address)
        Parameters
        ----------
        pad: int
            The device pad
        delay: float
            The time in seconds to wait after issuing the read request for the device before attempting to read back
            the answer.
        Returns
        -------
        bytearray

        """
        # Prepare read request command
        payload = bytes([pad, 0x0F])

        # Request read
        self.__device_write(UgPlusCommands.READ, payload)

        # Delay if necessary
        time.sleep(delay)

        # Read data sent from GPIB device
        try:
            byte_data = self.__device_read(UgPlusCommands.READ)
        except USBError as exc:
            if exc.errno == errno.ETIMEDOUT:
                self.__logger.error("Reading from device timed out.")
                return None
            raise

        if byte_data is None:
            return None

        # Strip the next two bytes, because the actual payload is prepended by a header containing the GPIB device ID
        # and a delimiter
        # addr = byte_data[0]
        success = byte_data[1] != 0x0A

        self.__logger.debug("Final USB read buffer: %(buffer)s.", {"buffer": self.__usb_read_buf})

        if not success:
            if len(self.__usb_read_buf) > 0:
                self.__logger.debug("Clearing USB read buffer.")
                self.__usb_read_buf = bytearray()  # clear usb read buffer
            raise OSError(
                errno.EIO, f"I/O error: Cannot read from GPIB device at address {pad}. Is the device attached?"
            )

        byte_data = byte_data[2:]

        # Strip final linefeed
        # byte_data = byte_data[:-1]

        # Convert to an ascii byte array
        # byte_data = binascii.b2a_qp(byte_data)

        return byte_data
