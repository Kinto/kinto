import argparse
import logging
import logging.config
import os
import subprocess
import sys

from pyramid.paster import bootstrap
from pyramid.scripts import pserve

from kinto import __version__
from kinto import scripts as kinto_scripts
from kinto.config import init
from kinto.core import scripts as core_scripts
from kinto.plugins.accounts import scripts as accounts_scripts

DEFAULT_CONFIG_FILE = os.getenv("KINTO_INI", "config/kinto.ini")
DEFAULT_PORT = 8888
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(levelname)-5.5s  %(message)s"


def main(args=None):
    """The main routine."""
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Kinto Command-Line Interface")
    commands = (
        "init",
        "start",
        "migrate",
        "flush-cache",
        "version",
        "rebuild-quotas",
        "create-user",
    )
    subparsers = parser.add_subparsers(
        title="subcommands",
        description="Main Kinto CLI commands",
        dest="subcommand",
        help="Choose and run with --help",
    )
    subparsers.required = True

    for command in commands:
        subparser = subparsers.add_parser(command)
        subparser.set_defaults(which=command)

        subparser.add_argument(
            "--ini",
            help="Application configuration file",
            dest="ini_file",
            required=False,
            default=DEFAULT_CONFIG_FILE,
        )

        subparser.add_argument(
            "-q",
            "--quiet",
            action="store_const",
            const=logging.CRITICAL,
            dest="verbosity",
            help="Show only critical errors.",
        )

        subparser.add_argument(
            "-v",
            "--debug",
            action="store_const",
            const=logging.DEBUG,
            dest="verbosity",
            help="Show all messages, including debug messages.",
        )

        if command == "init":
            subparser.add_argument(
                "--backend",
                help="{memory,redis,postgresql}",
                dest="backend",
                required=False,
                default=None,
            )
            subparser.add_argument(
                "--cache-backend",
                help="{memory,redis,postgresql,memcached}",
                dest="cache-backend",
                required=False,
                default=None,
            )
            subparser.add_argument(
                "--host",
                help="Host to listen() on.",
                dest="host",
                required=False,
                default="127.0.0.1",
            )

        elif command == "migrate":
            subparser.add_argument(
                "--dry-run",
                action="store_true",
                help="Simulate the migration operations and show information",
                dest="dry_run",
                required=False,
                default=False,
            )

        elif command == "rebuild-quotas":
            subparser.add_argument(
                "--dry-run",
                action="store_true",
                help="Simulate the rebuild operation and show information",
                dest="dry_run",
                required=False,
                default=False,
            )

        elif command == "start":
            subparser.add_argument(
                "--reload",
                action="store_true",
                help="Restart when code or config changes",
                required=False,
                default=False,
            )
            subparser.add_argument(
                "--port",
                type=int,
                help="Listening port number",
                required=False,
                default=DEFAULT_PORT,
            )

        elif command == "create-user":
            subparser.add_argument(
                "-u", "--username", help="Superuser username", required=False, default=None
            )
            subparser.add_argument(
                "-p", "--password", help="Superuser password", required=False, default=None
            )

    # Parse command-line arguments
    parsed_args = vars(parser.parse_args(args))

    config_file = parsed_args["ini_file"]
    which_command = parsed_args["which"]

    # Initialize logging from
    level = parsed_args.get("verbosity") or DEFAULT_LOG_LEVEL
    logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)

    if which_command == "init":
        if os.path.exists(config_file):
            print(f"{config_file} already exists.", file=sys.stderr)
            return 1

        backend = parsed_args["backend"]
        cache_backend = parsed_args["cache-backend"]
        if not backend:
            while True:
                prompt = (
                    "Select the backend you would like to use: "
                    "(1 - postgresql, 2 - redis, default - memory) "
                )
                answer = input(prompt).strip()
                try:
                    backends = {"1": "postgresql", "2": "redis", "": "memory"}
                    backend = backends[answer]
                    break
                except KeyError:
                    pass

        if not cache_backend:
            while True:
                prompt = (
                    "Select the cache backend you would like to use: "
                    "(1 - postgresql, 2 - redis, 3 - memcached, default - memory) "
                )
                answer = input(prompt).strip()
                try:
                    cache_backends = {
                        "1": "postgresql",
                        "2": "redis",
                        "3": "memcached",
                        "": "memory",
                    }
                    cache_backend = cache_backends[answer]
                    break
                except KeyError:
                    pass

        init(config_file, backend, cache_backend, parsed_args["host"])

        # Install postgresql libraries if necessary
        if backend == "postgresql" or cache_backend == "postgresql":
            try:
                import psycopg2  # NOQA
            except ImportError:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "kinto[postgresql]"]
                )
        elif backend == "redis" or cache_backend == "redis":
            try:
                import kinto_redis  # NOQA
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "kinto[redis]"])
        elif cache_backend == "memcached":
            try:
                import memcache  # NOQA
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "kinto[memcached]"])

    elif which_command == "migrate":
        dry_run = parsed_args["dry_run"]
        env = bootstrap(config_file, options={"command": "migrate"})
        core_scripts.migrate(env, dry_run=dry_run)

    elif which_command == "flush-cache":
        env = bootstrap(config_file, options={"command": "flush-cache"})
        core_scripts.flush_cache(env)

    elif which_command == "rebuild-quotas":
        dry_run = parsed_args["dry_run"]
        env = bootstrap(config_file, options={"command": "rebuild-quotas"})
        return kinto_scripts.rebuild_quotas(env, dry_run=dry_run)

    elif which_command == "create-user":
        username = parsed_args["username"]
        password = parsed_args["password"]
        env = bootstrap(config_file, options={"command": "create-user"})
        return accounts_scripts.create_user(env, username=username, password=password)

    elif which_command == "start":
        pserve_argv = ["pserve"]

        if parsed_args["reload"]:
            pserve_argv.append("--reload")

        if level == logging.DEBUG:
            pserve_argv.append("-v")

        if level == logging.CRITICAL:
            pserve_argv.append("-q")

        pserve_argv.append(config_file)
        pserve_argv.append(f"http_port={parsed_args['port']}")
        pserve.main(argv=pserve_argv)

    else:
        print(__version__)

    return 0
