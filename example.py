#!/usr/bin/env python3

# Copyright (C) 2015 Jacob Alexander
# Copyright (C) 2020 Patrick Baus
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

import logging
from ugGPIB.GPIB import UGPlusGPIB

### Program Entry Point ###

if __name__ == '__main__':
    # Initialize the UGSimpleGPIB USB adapter
    # Requires root permissions (or add the udev rule)
#    logging.basicConfig(level=logging.INFO)
    logging.basicConfig(level=logging.DEBUG)    # Enable logs from the adapter
    mygpib = UGPlusGPIB()

    # Firmware / Device Information
#    print("Manufacturer ID: {manufacturer}".format(manufacturer=mygpib.get_manufacturer_id()))
#    print("Model Number {}, Serial number: {}".format(*mygpib.get_serial_number()))
#    print("Firmware version: {}.{}".format(*mygpib.get_firmware_version()))


    # List Connected Devices
    try:
        print("Connected devices: {devices}".format(devices=mygpib.get_gpib_devices()))
#    mygpib.write(27, "*IDN?")
#    print("ID: {identifier}".format(identifier=mygpib.read(27)))
#    try:
        while True:
            mygpib.read(27, delay=1)
            print("Firmware version: {}.{}".format(*mygpib.get_firmware_version()))
#    mygpib.read(27, delay=2)
#    mygpib.read(27, delay=2)
#    except TypeError:
#        pass

    finally:
        mygpib.reset()
