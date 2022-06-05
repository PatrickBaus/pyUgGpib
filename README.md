# ug_gpib
Python3 pyUSB UGPlus GPIB Driver

Tested using Linux, should work for Mac OSX, Windows and any OS with Python [pyUSB](https://github.com/pyusb/pyusb)
support.

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

## Versioning

I use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/PatrickBaus/pyAsyncPrologix/tags). 

## Documentation
I use the [Numpydoc](https://numpydoc.readthedocs.io/en/latest/format.html) style for documentation.

## Authors

* **Jacob Alexander** - *Initial work for the UGSimple* [Jacob Alexander](https://github.com/haata)
* **Patrick Baus** - *Complete rewrite for the UGPlus* - [PatrickBaus](https://github.com/PatrickBaus)

## License


This project is licensed under the GPL v3 license - see the [LICENSE](LICENSE) file for details
