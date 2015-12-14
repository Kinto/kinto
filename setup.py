import os
import codecs
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


def read_file(filename):
    """Open a related file and return its content."""
    with codecs.open(os.path.join(here, filename), encoding='utf-8') as f:
        content = f.read()
    return content

README = read_file('README.rst')
CHANGELOG = read_file('CHANGELOG.rst')
CONTRIBUTORS = read_file('CONTRIBUTORS.rst')

REQUIREMENTS = [
    'waitress',
    'cliquet>=2.13,<3',
    'jsonschema',
]

POSTGRESQL_REQUIREMENTS = REQUIREMENTS + [
    'cliquet[postgresql]>=2.13,<3'
]

MONITORING_REQUIREMENTS = REQUIREMENTS + [
    'cliquet[monitoring]>=2.13,<3'
]

FXA_REQUIREMENTS = REQUIREMENTS + [
    'cliquet-fxa'
]

ENTRY_POINTS = {
    'paste.app_factory': [
        'main = kinto:main',
    ],
    'console_scripts': [
        'kinto = kinto.__main__:main'
    ],
}

DEPENDENCY_LINKS = [
]

setup(name='kinto',
      version='1.10.1',
      description='Kinto Web Service - Store, Sync, Share, and Self-Host.',
      long_description=README + "\n\n" + CHANGELOG + "\n\n" + CONTRIBUTORS,
      license='Apache License (2.0)',
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: Implementation :: CPython",
          "Programming Language :: Python :: Implementation :: PyPy",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
          "License :: OSI Approved :: Apache Software License"
      ],
      keywords="web services",
      author='Mozilla Services',
      author_email='services-dev@mozilla.com',
      url='https://github.com/Kinto/kinto',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=REQUIREMENTS,
      extras_require={
          'postgresql': POSTGRESQL_REQUIREMENTS,
          'monitoring': MONITORING_REQUIREMENTS,
          'fxa': FXA_REQUIREMENTS,
      },
      entry_points=ENTRY_POINTS,
      dependency_links=DEPENDENCY_LINKS)
