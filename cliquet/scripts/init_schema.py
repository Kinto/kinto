import logging
import optparse
import sys
import textwrap

from pyramid.paster import bootstrap


def main():
    description = """\
    Initialize storage and cache backend databases. Example:
    'init_schema deployment.ini'
    """
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    usage = "usage: %prog config_uri"
    parser = optparse.OptionParser(usage=usage,
                                   description=textwrap.dedent(description))
    options, args = parser.parse_args(sys.argv[1:])

    if not len(args) >= 1:
        logger.error('You must provide at least one argument')
        return 2

    config_uri = args[0]
    env = bootstrap(config_uri)

    cache_backend = env['registry'].cache
    cache_backend.initialize_schema()

    storage_backend = env['registry'].storage
    storage_backend.initialize_schema()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main() or 0)
