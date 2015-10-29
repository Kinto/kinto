import argparse
import sys
from cliquet.scripts import cliquet
from pyramid.scripts import pserve
from pyramid.paster import bootstrap


def create_parser():
        parser = argparse.ArgumentParser(description="Kinto commands")
        subparsers = parser.add_subparsers(title='subcommands',
                                           description='valid subcommands',
                                           help='init/start/migrate')

        parser_init = subparsers.add_parser('init')
        parser_init.set_defaults(which='init')
        parser_init.add_argument('--config_file', required=False,
                                 help='Config file may be passed as argument')

        parser_migrate = subparsers.add_parser('migrate')
        parser_migrate.set_defaults(which='migrate')

        parser_start = subparsers.add_parser('start')
        parser_start.set_defaults(which='start')

        return parser


def main(args=None):
        """The main routine."""
        if args is None:
                args = sys.argv[1:]

        parser = create_parser()

        args = vars(parser.parse_args())

        if args['which'] == 'init':
                if(args['config_file'] is None):
                    env = bootstrap('config/kinto.ini')
                else:
                    config_file = format(args['config_file'])
                    env = bootstrap(config_file)
        elif args['which'] == 'migrate':
                env = bootstrap('config/kinto.ini')
                cliquet.init_schema(env)
        elif args['which'] == 'start':
                pserve_argv = ['pserve', 'config/kinto.ini', '--reload']
                pserve.main(pserve_argv)


if __name__ == "__main__":
        main()
