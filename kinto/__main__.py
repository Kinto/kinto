import argparse
import sys
from cliquet.scripts import cliquet
from pyramid.scripts import pserve
from pyramid.paster import bootstrap


def main(args=None):
        """The main routine."""
        if args is None:
                args = sys.argv[1:]

        parser = argparse.ArgumentParser(description="Kinto commands")
        subparsers = parser.add_subparsers(title='subcommands',
                                           description='valid subcommands',
                                           help='start/migrate')

        parser_init = subparsers.add_parser('init')
        parser_init.set_defaults(which='init')

        parser_migrate = subparsers.add_parser('migrate')
        parser_migrate.set_defaults(which='migrate')

        parser_start = subparsers.add_parser('start')
        parser_start.set_defaults(which='start')

        args = vars(parser.parse_args())

        if args['which'] == 'init':
                """Still needs to setup the configuration options"""
                pass
        elif args['which'] == 'migrate':
                env = bootstrap('config/kinto.ini')
                """kinto_migrate(env)"""
                cliquet.init_schema(env)
                print("running migrations")
        elif args['which'] == 'start':
                pserve_argv = ['pserve', 'config/kinto.ini', '--reload']
                pserve.main(pserve_argv)


if __name__ == "__main__":
        main()
