# ug_gpib
Python3 pyUSB UGPlus GPIB Driver

Tested using Linux, should work for Mac OSX, Windows and any OS with Python [pyUSB](https://github.com/pyusb/pyusb)
support.

The [UGPlus](http://lqelectronics.com/Products/USBUG/UGPlus/UGPlus.html) is a fairly cheap, that supports simple GPIB
read and write operations only. It does not support advanced GPIB features like serial polling for example. It does not
have line drivers as well.

The UGPlus does have several firmware bugs, I have tried to mitigate them to the best of my knowledge. See
[below](#firmware-bugs) for details.

If you are looking for advanced features I suggest buying either a Prologix GPIB adapter or one of the NI USB adapters.
I can recommend the following libraries for both
[Prologix GPIB adapter](https://github.com/PatrickBaus/pyAsyncPrologixGpib) and
[Linux GPIB](https://github.com/PatrickBaus/pyAsyncGpib).

## Setup

To install the library in a virtual environment (always use venvs with every project):

```bash
virtualenv env  # virtual environment, optional
source env/bin/activate
pip install git+https://github.com/PatrickBaus/pyUgGpib.git
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
gpib_controller.write(2, b'*IDN?\n')
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

I have also had problems when using the adapter with an HP3478A. This device consistently crashed the adapter and only
power cycling brought it back to life. The HP3478A is not SCPI compliant, so the issue might lie there.

## Versioning

I use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/PatrickBaus/pyAsyncPrologix/tags). 

## Documentation
I use the [Numpydoc](https://numpydoc.readthedocs.io/en/latest/format.html) style for documentation.

## Authors

* **Jacob Alexander** - *Initial work for the UGSimple* [Jacob Alexander](https://github.com/haata)
* **Patrick Baus** - *Complete rewrite for the UGPlus* - [PatrickBaus](https://github.com/PatrickBaus)

## License


This project is licensed under the GPL v3 license - see the [LICENSE](LICENSE) file for details
