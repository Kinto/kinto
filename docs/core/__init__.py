import os
import os.path
import pkg_resources


def copy_docs(section, destination):
    if not os.path.exists(destination):
        os.makedirs(destination)

    for doc_name in pkg_resources.resource_listdir('cliquet_docs', section):
        resource_file = '%s/%s' % (section, doc_name)
        stream = pkg_resources.resource_stream('cliquet_docs', resource_file)
        dest_filename = os.path.join(destination, doc_name)
        with open(dest_filename, 'wb') as f:
            f.write(stream.read())
