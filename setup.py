import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

REQUIREMENTS = [
    'colander',
    'cornice',
    'pyfxa',
    'pyramid_multiauth',
    'requests',
    'waitress',
    'six',
]
DEPENDENCY_LINKS = [
    'https://github.com/mozilla/PyFxA/tarball/sqlalchemy#egg=PyFxA-0.0.2dev',
]
ENTRY_POINTS = {
    'paste.app_factory': [
        'main = readinglist:main',
    ]}


setup(name='readinglist',
      version=0.1,
      description='readinglist',
      long_description=README,
      classifiers=[
          "Programming Language :: Python",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"
      ],
      keywords="web services",
      author='',
      author_email='',
      url='',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=REQUIREMENTS,
      dependency_links=DEPENDENCY_LINKS,
      entry_points=ENTRY_POINTS)
