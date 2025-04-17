import configparser
import logging.config
import os

from kinto import main

here = os.path.dirname(__file__)

ini_path = os.environ.get('KINTO_INI')
if ini_path is None:
    # WARNING: if you modify this default value, you should
    # also change the default in `kinto.config.config_attributes()`
    ini_path = os.path.join(here, 'config', 'kinto.ini')

# Set up logging
logging.config.fileConfig(ini_path)

# Parse config and create WSGI app
config = configparser.ConfigParser()
config.read(ini_path)

application = main(config.items('DEFAULT'), **dict(config.items('app:main')))
