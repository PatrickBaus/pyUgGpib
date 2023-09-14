[![pylint](../../actions/workflows/pylint.yml/badge.svg)](../../actions/workflows/pylint.yml)
[![PyPI](https://img.shields.io/pypi/v/ug-gpib)](https://pypi.org/project/ug-gpib/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ug-gpib)
![PyPI - Status](https://img.shields.io/pypi/status/ug-gpib)
[![code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
# ug_gpib
A Python3 pyUSB driver for the LQ Electronics Corp UGPlus USB to GPIB Controller.

Tested using Linux, should work for Mac OSX, Windows and any OS with Python [pyUSB](https://github.com/pyusb/pyusb)
support.

:warning: **The device must be IEEE 488.1 compliant. It must assert the EOI line to signal the end of a line. If this is
not the case, the controller cannot be used. Older devices, typically only send CR, LF, or CR-LF.**

The [UGPlus](http://lqelectronics.com/Products/USBUG/UGPlus/UGPlus.html) is a fairly cheap controller, that supports
simple GPIB read and write operations only. It does not support advanced GPIB features like serial polling for example,
and it does not have line drivers to support long cables and lots of devices on the bus.

The UGPlus does have several firmware bugs, I have tried to mitigate them to the best of my knowledge. See
[below](#firmware-bugs) for details.

If you are looking for advanced features I suggest buying either a Prologix GPIB adapter or one of the NI USB adapters.
I can recommend the following libraries for both
[Prologix GPIB adapter](https://github.com/PatrickBaus/pyAsyncPrologixGpib) and
[Linux GPIB](https://github.com/PatrickBaus/pyAsyncGpib).

The library is fully type-hinted.

## Setup

To install the library in a virtual environment (always use venvs with every project):

```bash
virtualenv env  # virtual environment, optional
source env/bin/activate
pip install ug-gpib
```

### Linux
To access the raw usb port in Linux, root privileges are required. It is possible to use udev to change ownership of the
usb port on creation. This can be done via a rules file.

```bash
sudo cp 98-ugsimple.rules /etc/udev/rules.d/.
sudo udevadm control --reload-rules
```

## Usage

Initialize UGSimpleGPIB

```python
from ug_gpib import UGPlusGpib

gpib_controller = UGPlusGpib()
```

Writing "*IDN?" a command to address 0x02. Do note the GPIB commands must be byte strings.
```python
gpib_controller.write(2, b"*IDN?\n")
```

Reading from address 0x02 and decoding the byte string to a unicode string.
```python
data = gpib_controller.read(2)
print(data.decode())
```

See [examples/](examples/) for more working examples. Including an example that shows how to use the library from the
command line.

## Firmware Bugs
There are several bugs in the firmware of the UGPlus most of those are off-by-one errors and consequently out-of-bounds
reads. I documented them
[here](https://github.com/PatrickBaus/pyUgGpib/blob/f1bb0d2244304b3e3f9776606918eaa270d0e9dc/ug_gpib/ug_gpib.py#L152).
Some of these bugs are also evident when using the software supplied by the manufacturer.
The most obvious ones are the following:

* Out-of-bounds read when reading the firmware version. The controller sends one more byte than requested.
* Out-of-bounds read when discovering GPIB devices. The controller sends one more byte than requested.
* Out-of-bounds read when the GPIB device does not return any data. The controller sends one more byte than requested.

## Versioning

I use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](../../tags). 

## Documentation
I use the [Numpydoc](https://numpydoc.readthedocs.io/en/latest/format.html) style for documentation.

## Authors

* **Jacob Alexander** - *Initial work for the UGSimple* [Jacob Alexander](https://github.com/haata)
* **Patrick Baus** - *Complete rewrite for the UGPlus* - [PatrickBaus](https://github.com/PatrickBaus)

## License


This project is licensed under the GPL v3 license - see the [LICENSE](LICENSE) file for details
