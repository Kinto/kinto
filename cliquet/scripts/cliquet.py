import logging
import argparse
import sys
import textwrap

from pyramid.paster import bootstrap


def init_schema(env):
    cache_backend = env['registry'].cache
    cache_backend.initialize_schema()

    storage_backend = env['registry'].storage
    storage_backend.initialize_schema()


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

    subparsers = parser.add_subparsers()
    parser_init_schema = subparsers.add_parser('init')
    parser_init_schema.set_defaults(func=init_schema)

    args = parser.parse_args(sys.argv[1:])

    env = bootstrap(args.ini_file)
    args.func(env)


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main() or 0)
