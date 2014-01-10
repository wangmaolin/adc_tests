from setuptools import setup

__version__ = '0.1'

setup(name = 'adc5g',
      version = __version__,
      description = 'Code for testing and interacting with the ASIAA 5 GSps ADC (https://casper.berkeley.edu/wiki/ADC1x5000-8). This code originally based on that created by the Harvard Center for AStrophysics SMA team (https://github.com/sma-wideband/adc_tests)',
      url = "https://github.com/jack-h/adc_tools",
      requires    = ['numpy', 'corr'],
      provides    = ['adc5g'],
      package_dir = {'adc5g':'src'},
      packages    = ['adc5g'],
)

