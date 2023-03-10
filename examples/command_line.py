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
This example can be used to pipe a file with commands to a GPIB device.
Usage: cat commands.txt | ./command_line.py
"""
import sys

from ug_gpib import UGPlusGpib

if __name__ == "__main__":
    # Initialize the UGSimpleGPIB USB adapter
    # Requires root permissions (or add the udev rule)
    gpib_controller = UGPlusGpib(timeout=1)
    pad = 9  # pylint: disable=invalid-name
    # Read commands from the stdin line by line and feed it to the GPIB device
    for line in sys.stdin:
        gpib_controller.write(pad, line.encode("ascii"))
