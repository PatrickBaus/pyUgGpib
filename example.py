#!/usr/bin/env python3

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

import logging
from ugGPIB.GPIB import UGPlusGPIB
import time
import sys

### Program Entry Point ###

if __name__ == '__main__':
    # Initialize the UGSimpleGPIB USB adapter
    # Requires root permissions (or add the udev rule)
    logging.basicConfig(level=logging.INFO)
#    logging.basicConfig(level=logging.DEBUG)    # Enable logs from the adapter
    mygpib = UGPlusGPIB()

    # Firmware / Device Information
    print("Manufacturer ID: {manufacturer}".format(manufacturer=mygpib.get_manufacturer_id()))
    print("Model Number {}, Serial number: {}".format(*mygpib.get_serial_number()))
    print("Firmware version: {}.{}".format(*mygpib.get_firmware_version()))

#    mygpib.reset()
    # Firmware / Device Information
#    print("Manufacturer ID: {manufacturer}".format(manufacturer=mygpib.manufacturer_id()))
#    print("Firmware version: {version}".format(version=mygpib.firmware_version()))
#    print("Serial number: {serial}".format(serial=mygpib.series_number()))

    # List Connected Devices
    print("Connected devices: {devices}".format(devices=mygpib.get_gpib_devices()))

    sys.exit()
    # GPIB Commands
    print("Beeping three times")
    mygpib.write(22, "END ALWAYS")
    time.sleep(0.3)
    mygpib.write(22, "BEEP" )
    time.sleep(0.3)
    mygpib.write(22, "BEEP" )
    time.sleep(0.3)
    mygpib.write(22, "BEEP" )
    time.sleep(0.3)
    print("Getting device type")
    mygpib.write(22, "ID?")
    time.sleep(0.3)
    reply = mygpib.read(22, delay=1)
    print(reply)
    # Read Version Info
    print("Getting device firmware version")
    print(mygpib.read(22))
