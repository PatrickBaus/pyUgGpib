#!/usr/bin/env python
# ##### BEGIN GPL LICENSE BLOCK #####
#
# Copyright (C) 2022  Patrick Baus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####
"""
This is a basic example showing how to
"""

import logging
import time

from ug_gpib import UGPlusGpib

if __name__ == "__main__":
    # Initialize the UGPlusGPIB USB adapter
    # Requires root permissions (or add the udev rule)
    logging.basicConfig(level=logging.INFO)  # Enable logs from the adapter, set to DEBUG for more verbose output
    gpib_controller = UGPlusGpib(timeout=1)  # timeout in seconds
    gpib_controller.write(9, b"*RST\n")
    time.sleep(1)  # Need to wait after reset

    # Firmware / Device Information
    model, series = gpib_controller.get_series_number()
    print(f"Model Number {model}, Series number: {series}")
    print("Firmware version: {}.{}".format(*gpib_controller.version()))  # pylint: disable=consider-using-f-string

    # List connected devices
    try:
        gpib_controller.write(9, b"*IDN?\n")
        print(f"ID: {gpib_controller.read(9).decode()}")  # type:ignore

    finally:
        gpib_controller.reset()
