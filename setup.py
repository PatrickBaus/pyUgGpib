import re
from setuptools import setup

with open('README.md', 'r') as f:
    long_description = f.read()

# Read the version information from the verion file
VERSION_FILE = "ug_gpib/_version.py"
VERSION_REGEX = r'^__version__ = [\'"]([^\'"]+)[\'"]$'
with open(VERSION_FILE, 'r') as f:
    version = f.read()
    result = re.search(VERSION_REGEX, version, re.M)
    if result:
        version = result.group(1)
    else:
        raise RuntimeError('No version string found in file %s.', VERSION_FILE)

setup(
   name='ug_gpib',
   version=version,
   author='Patrick Baus',
   author_email='patrick.baus@physik.tu-darmstadt.de',
   url='https://github.com/PatrickBaus/pyUgGpib',
   description='A Python library for the LQ Electronics Corp UGPlus USB GPIB adapter',
   long_description=long_description,
   classifiers=[
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Programming Language :: Python',
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Natural Language :: English',
    'Topic :: Home Automation',
   ],
   keywords='UGPlus GPIB API',
   license='GPL',
   license_files=('LICENSE',),
   packages=['ug_gpib'],  # same as name
   install_requires=['pyusb', ],  # external packages as dependencies
)
