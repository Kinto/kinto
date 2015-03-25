import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

with open(os.path.join(here, 'CHANGELOG.rst')) as f:
    CHANGELOG = f.read()

with open(os.path.join(here, 'CONTRIBUTORS.rst')) as f:
    CONTRIBUTORS = f.read()


REQUIREMENTS = [
    'colander',
    'cornice >= 0.20',  # Fixes cors.
    'python-dateutil',
    'pyfxa >= 0.0.3',  # Has cache support.
    'pyramid_multiauth',
    'redis',  # Default backend
    'requests',
    'six',
    'structlog',
    'ujson',
]

POSTGRESQL_REQUIRES = [
    'psycopg2>2.5',
]

MONITORING_REQUIRES = [
    'raven',
    'statsd',
]

setup(name='cliquet',
      version='1.4.2.dev0',
      description='cliquet',
      long_description=README + "\n\n" + CHANGELOG + "\n\n" + CONTRIBUTORS,
      license='Apache License (2.0)',
      classifiers=[
          "Programming Language :: Python",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
          "License :: OSI Approved :: Apache Software License"
      ],
      keywords="web services",
      author='Mozilla Services',
      author_email='services-dev@mozilla.com',
      url='',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=REQUIREMENTS,
      extras_require={
          'postgresql': REQUIREMENTS + POSTGRESQL_REQUIRES,
          'monitoring': REQUIREMENTS + MONITORING_REQUIRES,
      })
