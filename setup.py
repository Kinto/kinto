import platform
import codecs
import os
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

installed_with_pypy = platform.python_implementation() == 'PyPy'

REQUIREMENTS = [
    'colander',
    'colorama',
    'cornice >= 1.1',  # Fix cache CORS
    'jsonschema',
    'python-dateutil',
    'pyramid_multiauth >= 0.8',  # User on policy selected event.
    'pyramid_tm',
    'redis',  # Default backend
    'requests',
    'six',
    'structlog',
    'enum34',
    'waitress',
]

if installed_with_pypy:
    # We install psycopg2cffi instead of psycopg2 when dealing with pypy
    # Note: JSONB support landed after psycopg2cffi 2.7.0
    POSTGRESQL_REQUIRES = [
        'SQLAlchemy',
        'psycopg2cffi>2.7.0',
        'zope.sqlalchemy',
    ]
else:
    # ujson is not pypy compliant, as it uses the CPython C API
    REQUIREMENTS.append('ujson >= 1.35')
    POSTGRESQL_REQUIRES = [
        'SQLAlchemy',
        'psycopg2>2.5',
        'zope.sqlalchemy',
    ]

DEPENDENCY_LINKS = [
]

MONITORING_REQUIRES = [
    'raven',
    'statsd',
    'newrelic',
    'werkzeug',
]

ENTRY_POINTS = {
    'paste.app_factory': [
        'main = kinto:main',
    ],
    'console_scripts': [
        'kinto = kinto.__main__:main'
    ],
}


setup(name='kinto',
      version='3.0.0',
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
      keywords="web sync json storage services",
      author='Mozilla Services',
      author_email='storage-team@mozilla.com',
      url='https://github.com/Kinto/kinto',
      packages=find_packages(),
      package_data={'': ['*.rst', '*.py']},
      include_package_data=True,
      zip_safe=False,
      install_requires=REQUIREMENTS,
      extras_require={
          'postgresql': POSTGRESQL_REQUIRES,
          'monitoring': MONITORING_REQUIRES,
          ":python_version=='2.7'": ["functools32"],
      },
      test_suite="kinto.tests",
      dependency_links=DEPENDENCY_LINKS,
      entry_points=ENTRY_POINTS)
