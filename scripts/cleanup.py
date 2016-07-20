from __future__ import print_function
import argparse
import warnings
import sys
from pyramid.paster import bootstrap
from pyramid.settings import asbool


CONFIG_FILE = 'config/kinto.ini'
DEFAULT_COLLECTION = '/buckets/blocklists/collections/certificates,'


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

    parser.add_argument('--collection',
                        help='Collection to cleanup',
                        dest='collection',
                        required=True,
                        default=DEFAULT_COLLECTION)

    parsed_args = vars(parser.parse_args(args))

    config_file = parsed_args['ini_file']
    collection = parsed_args['collection']

    env = bootstrap(config_file)
    registry = env['registry']
    settings = registry.settings
    readonly_mode = asbool(settings.get('readonly', False))

    if readonly_mode:
        message = ('Cannot cleanup the collection while in readonly mode.')
        warnings.warn(message)
        sys.exit(1)

    try:
        _, bucket_id, _, collection_id = collection.strip('/').split('/')
    except ValueError:
        sys.stderr.write('%r should be of the form: /buckets/{bucket_id}'
                         '/collections/{collection_id}\n' % collection)
        sys.exit(2)

    deleted = registry.storage.delete_all('record', collection,
                                          with_deleted=False)
    print('%d records have been deleted.' % len(deleted))

    bucket = '/buckets/%s' % bucket_id
    registry.storage.delete('collection', bucket, collection_id,
                            with_deleted=False)
    print('%r collection have been deleted' % collection)


if __name__ == '__main__':
    main()
