import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

with open(os.path.join(here, 'CHANGELOG.rst')) as f:
    CHANGELOG = f.read()


REQUIREMENTS = [
    'colander==1.0',
    'cornice==1.0.0',
    'six==1.9.0',
    'waitress==0.8.9',
    'cliquet[monitoring]==2.1.0'
]

ENTRY_POINTS = {
    'paste.app_factory': [
        'main = kinto:main',
    ]}

DEPENDENCY_LINKS = [
]

setup(name='kinto',
      version='1.2.0.dev0',
      description='kinto',
      long_description=README + "\n\n" + CHANGELOG,
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
      entry_points=ENTRY_POINTS,
      dependency_links=DEPENDENCY_LINKS)
