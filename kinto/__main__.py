from __future__ import print_function
import argparse
import os
import sys
from cliquet.scripts import cliquet
from pyramid.scripts import pserve
from pyramid.paster import bootstrap

from kinto.config import init

CONFIG_FILE = 'config/kinto.ini'


def main(args=None):
    """The main routine."""
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Kinto commands")
    parser.add_argument('--ini',
                        help='Application configuration file',
                        dest='ini_file',
                        required=False,
                        default=CONFIG_FILE)

    subparsers = parser.add_subparsers(title='subcommands',
                                       description='valid subcommands',
                                       help='init/start/migrate')

    parser_init = subparsers.add_parser('init')
    parser_init.set_defaults(which='init')

    parser_migrate = subparsers.add_parser('migrate')
    parser_migrate.set_defaults(which='migrate')

    parser_start = subparsers.add_parser('start')
    parser_start.set_defaults(which='start')

    args = vars(parser.parse_args())
    config_file = args['ini_file']

    if args['which'] == 'init':
        if not os.path.exists(config_file):
            init(config_file)
        else:
            print("%s already exist." % config_file, file=sys.stderr)
            sys.exit(1)

    elif args['which'] == 'migrate':
        env = bootstrap(config_file)
        cliquet.init_schema(env)

    elif args['which'] == 'start':
        pserve_argv = ['pserve', config_file, '--reload']
        pserve.main(pserve_argv)


if __name__ == "__main__":
    main()
