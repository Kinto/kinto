from __future__ import absolute_import, print_function
import logging
import argparse
import sys
import textwrap
import warnings

from pyramid.paster import bootstrap
from pyramid.settings import asbool

from cliquet import __version__


def deprecated_init(env):
    message = '"cliquet init" is deprecated. Use "cliquet migrate" instead.'
    warnings.warn(message, DeprecationWarning)
    init_schema(env)


def init_schema(env):
    registry = env['registry']
    settings = registry.settings
    readonly_backends = ('storage', 'permission')
    readonly_mode = asbool(settings.get('readonly', False))

    for backend in ('cache', 'storage', 'permission'):
        if hasattr(registry, backend):
            if readonly_mode and backend in readonly_backends:
                message = ('Cannot migrate the %s backend while '
                           'in readonly mode.' % backend)
                warnings.warn(message)
            else:
                getattr(registry, backend).initialize_schema()


def main():
    description = """\
    Cliquet administration commands.
    """
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description=textwrap.dedent(description))
    parser.add_argument('--ini',
                        help='Application configuration file',
                        dest='ini_file',
                        required=True)
    parser.add_argument('-v', '--version',
                        action='version', version=__version__,
                        help='Print the cliquet version and exit.')

    subparsers = parser.add_subparsers()

    parser_deprecated_init = subparsers.add_parser('init')
    parser_deprecated_init.set_defaults(func=deprecated_init)
    parser_init_schema = subparsers.add_parser('migrate')
    parser_init_schema.set_defaults(func=init_schema)

    args = parser.parse_args(sys.argv[1:])

    env = bootstrap(args.ini_file)
    args.func(env)


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main() or 0)
