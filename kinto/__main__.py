import argparse
import os
import sys
import logging
import logging.config

from kinto.core import scripts
from pyramid.scripts import pserve
from pyramid.paster import bootstrap
from kinto import __version__
from kinto.config import init

DEFAULT_CONFIG_FILE = 'config/kinto.ini'
DEFAULT_PORT = 8888
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(levelname)-5.5s  %(message)s"


def main(args=None):
    """The main routine."""
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Kinto Command-Line "
                                                 "Interface")
    commands = ('init', 'start', 'migrate', 'delete-collection', 'version',
                'rebuild-quotas')
    subparsers = parser.add_subparsers(title='subcommands',
                                       description='Main Kinto CLI commands',
                                       dest='subcommand',
                                       help="Choose and run with --help")
    subparsers.required = True

    for command in commands:
        subparser = subparsers.add_parser(command)
        subparser.set_defaults(which=command)

        subparser.add_argument('--ini',
                               help='Application configuration file',
                               dest='ini_file',
                               required=False,
                               default=DEFAULT_CONFIG_FILE)

        subparser.add_argument('-q', '--quiet', action='store_const',
                               const=logging.CRITICAL, dest='verbosity',
                               help='Show only critical errors.')

        subparser.add_argument('-v', '--debug', action='store_const',
                               const=logging.DEBUG, dest='verbosity',
                               help='Show all messages, including debug messages.')

        if command == 'init':
            subparser.add_argument('--backend',
                                   help='{memory,redis,postgresql}',
                                   dest='backend',
                                   required=False,
                                   default=None)
            subparser.add_argument('--host',
                                   help='Host to listen() on.',
                                   dest='host',
                                   required=False,
                                   default='127.0.0.1')
        elif command == 'migrate':
            subparser.add_argument('--dry-run',
                                   action='store_true',
                                   help='Simulate the migration operations '
                                        'and show information',
                                   dest='dry_run',
                                   required=False,
                                   default=False)
        elif command == 'delete-collection':
            subparser.add_argument('--bucket',
                                   help='The bucket where the collection '
                                        'belongs to.',
                                   required=True)
            subparser.add_argument('--collection',
                                   help='The collection to remove.',
                                   required=True)

        elif command == 'rebuild-quotas':
            subparser.add_argument('--dry-run',
                                   action='store_true',
                                   help='Simulate the rebuild operation '
                                        'and show information',
                                   dest='dry_run',
                                   required=False,
                                   default=False)

        elif command == 'start':
            subparser.add_argument('--reload',
                                   action='store_true',
                                   help='Restart when code or config changes',
                                   required=False,
                                   default=False)
            subparser.add_argument('--port',
                                   type=int,
                                   help='Listening port number',
                                   required=False,
                                   default=DEFAULT_PORT)

    # Parse command-line arguments
    parsed_args = vars(parser.parse_args(args))

    config_file = parsed_args['ini_file']
    which_command = parsed_args['which']

    # Initialize logging from
    level = parsed_args.get('verbosity') or DEFAULT_LOG_LEVEL
    logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)

    if which_command == 'init':
        if os.path.exists(config_file):
            print("{} already exists.".format(config_file), file=sys.stderr)
            return 1

        backend = parsed_args['backend']
        if not backend:
            while True:
                prompt = ("Select the backend you would like to use: "
                          "(1 - postgresql, 2 - redis, default - memory) ")
                answer = input(prompt).strip()
                try:
                    backends = {"1": "postgresql", "2": "redis", "": "memory"}
                    backend = backends[answer]
                    break
                except KeyError:
                    pass

        init(config_file, backend, parsed_args['host'])

        # Install postgresql libraries if necessary
        if backend == "postgresql":
            try:
                import psycopg2  # NOQA
            except ImportError:
                import pip
                pip.main(['install', "kinto[postgresql]"])
        elif backend == "redis":
            try:
                import kinto_redis  # NOQA
            except ImportError:
                import pip
                pip.main(['install', "kinto[redis]"])

    elif which_command == 'migrate':
        dry_run = parsed_args['dry_run']
        env = bootstrap(config_file)
        scripts.migrate(env, dry_run=dry_run)

    elif which_command == 'delete-collection':
        env = bootstrap(config_file)
        return scripts.delete_collection(env,
                                         parsed_args['bucket'],
                                         parsed_args['collection'])

    elif which_command == 'rebuild-quotas':
        dry_run = parsed_args['dry_run']
        env = bootstrap(config_file)
        return scripts.rebuild_quotas(env, dry_run=dry_run)

    elif which_command == 'start':
        pserve_argv = ['pserve']

        if parsed_args['reload']:
            pserve_argv.append('--reload')

        if level == logging.DEBUG:
            pserve_argv.append('-v')

        if level == logging.CRITICAL:
            pserve_argv.append('-q')

        pserve_argv.append(config_file)
        pserve_argv.append('http_port={}'.format(parsed_args['port']))
        pserve.main(argv=pserve_argv)

    else:
        print(__version__)

    return 0
