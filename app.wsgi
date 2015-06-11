try:
    import ConfigParser as configparser
except ImportError:
    import configparser
import logging.config
import os

from kinto import main

here = os.path.dirname(__file__)

ini_path = os.environ.get('KINTO_INI')
if ini_path is None:
    ini_path = os.path.join(here, 'config', 'kinto.ini')

# Set up logging
logging.config.fileConfig(ini_path)

# Parse config and create WSGI app
config = configparser.ConfigParser()
config.read(ini_path)

application = main(config.items('DEFAULT'), **dict(config.items('app:main')))
