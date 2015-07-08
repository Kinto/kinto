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
    'waitress==0.8.9',
    'cliquet==2.2.1'
]

POSTGRESQL_REQUIREMENTS = REQUIREMENTS + [
    'cliquet[postgresql]==2.2.1'
]

MONITORING_REQUIREMENTS = REQUIREMENTS + [
    'cliquet[monitoring]==2.2.1'
]

FXA_REQUIREMENTS = REQUIREMENTS + [
    'cliquet-fxa==1.0.0'
]

ENTRY_POINTS = {
    'paste.app_factory': [
        'main = kinto:main',
    ]}

DEPENDENCY_LINKS = [
]

setup(name='kinto',
      version='1.2.1',
      description='kinto',
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
          'postgresql': POSTGRESQL_REQUIREMENTS,
          'monitoring': MONITORING_REQUIREMENTS,
          'fxa': FXA_REQUIREMENTS,
      },
      entry_points=ENTRY_POINTS,
      dependency_links=DEPENDENCY_LINKS)
