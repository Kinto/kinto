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
    'cornice',
    'python-dateutil',
    'pyfxa',
    'pyramid_multiauth',
    'redis',  # Session backend
    'requests',
    'six',
]

POSTGRESQL_REQUIRES = [
    'psycopg2>2.5',
]

setup(name='cliquet',
      version='1.1.4',
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
      })
