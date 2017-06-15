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

REQUIREMENTS = [
    'bcrypt',
    'colander >= 1.3.2',
    'cornice >= 2.4',
    'cornice_swagger >= 0.5.1',
    'jsonschema',
    'jsonpatch',
    'logging-color-formatter >= 1.0.1',  # Message interpolations.
    'python-dateutil',
    'pyramid > 1.8',
    'pyramid_multiauth >= 0.8',  # User on policy selected event.
    'transaction',
    'pyramid_tm < 2',
    'requests',
    'waitress',
    'ujson >= 1.35'
]

POSTGRESQL_REQUIRES = [
    'SQLAlchemy',
    'psycopg2 > 2.5',
    'zope.sqlalchemy',
]

REDIS_REQUIRES = [
    'kinto_redis'
]

SETUP_REQUIRES = [
    'pytest-runner'
]

TEST_REQUIREMENTS = [
    'bravado_core',
    'pytest',
    'WebTest'
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
      version='7.2.0',
      description='Kinto Web Service - Store, Sync, Share, and Self-Host.',
      long_description="{}\n\n{}\n\n{}".format(README, CHANGELOG, CONTRIBUTORS),
      license='Apache License (2.0)',
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: Implementation :: CPython",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
          "License :: OSI Approved :: Apache Software License"
      ],
      keywords="web sync json storage services",
      author='Mozilla Services',
      author_email='storage-team@mozilla.com',
      url='https://github.com/Kinto/kinto',
      packages=find_packages(),
      package_data={'': ['*.rst', '*.py', '*.yaml']},
      include_package_data=True,
      zip_safe=False,
      setup_requires=SETUP_REQUIRES,
      tests_require=TEST_REQUIREMENTS,
      install_requires=REQUIREMENTS,
      extras_require={
          'redis': REDIS_REQUIRES,
          'postgresql': POSTGRESQL_REQUIRES,
          'monitoring': MONITORING_REQUIRES,
      },
      test_suite="tests",
      dependency_links=DEPENDENCY_LINKS,
      entry_points=ENTRY_POINTS)
