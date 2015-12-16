# (c) 2005 Ian Bicking and contributors; written for Paste
# (http://pythonpaste.org) Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php

import optparse
import os
import os.path
import pkg_resources
import re
import sys

_bad_chars_re = re.compile('[^a-zA-Z0-9_]')

def main(argv=sys.argv, quiet=False):
    command = PCreateCommand(argv, quiet)
    return command.run()

class PCreateCommand(object):
    verbosity = 1 # required
    description = "Render Pyramid scaffolding to an output directory"
    usage = "usage: %prog [options] output_directory"
    parser = optparse.OptionParser(usage, description=description)
    parser.add_option('-s', '--scaffold',
                      dest='scaffold_name',
                      action='append',
                      help=("Add a scaffold to the create process "
                            "(multiple -s args accepted)"))
    parser.add_option('-t', '--template',
                      dest='scaffold_name',
                      action='append',
                      help=('A backwards compatibility alias for '
                            '-s/--scaffold.  Add a scaffold to the '
                            'create process (multiple -t args accepted)'))
    parser.add_option('-l', '--list',
                      dest='list',
                      action='store_true',
                      help="List all available scaffold names")
    parser.add_option('--list-templates',
                      dest='list',
                      action='store_true',
                      help=("A backwards compatibility alias for -l/--list.  "
                            "List all available scaffold names."))
    parser.add_option('--simulate',
                      dest='simulate',
                      action='store_true',
                      help='Simulate but do no work')
    parser.add_option('--overwrite',
                      dest='overwrite',
                      action='store_true',
                      help='Always overwrite')
    parser.add_option('--interactive',
                      dest='interactive',
                      action='store_true',
                      help='When a file would be overwritten, interrogate')

    pyramid_dist = pkg_resources.get_distribution("pyramid")

    def __init__(self, argv, quiet=False):
        self.quiet = quiet
        self.options, self.args = self.parser.parse_args(argv[1:])
        self.scaffolds = self.all_scaffolds()

    def run(self):
        if self.options.list:
            return self.show_scaffolds()
        if not self.options.scaffold_name:
            self.out('You must provide at least one scaffold name')
            return 2
        if not self.args:
            self.out('You must provide a project name')
            return 2
        available = [x.name for x in self.scaffolds]
        diff = set(self.options.scaffold_name).difference(available)
        if diff:
            self.out('Unavailable scaffolds: %s' % list(diff))
            return 2
        return self.render_scaffolds()

    def render_scaffolds(self):
        options = self.options
        args = self.args
        output_dir = os.path.abspath(os.path.normpath(args[0]))
        project_name = os.path.basename(os.path.split(output_dir)[1])
        pkg_name = _bad_chars_re.sub('', project_name.lower())
        safe_name = pkg_resources.safe_name(project_name)
        egg_name = pkg_resources.to_filename(safe_name)

        # get pyramid package version
        pyramid_version = self.pyramid_dist.version

        ## map pyramid package version of the documentation branch ##
        # if version ends with 'dev' then docs version is 'master'
        if self.pyramid_dist.version[-3:] == 'dev':
            pyramid_docs_branch = 'master'
        else:
            # if not version is not 'dev' find the version.major_version string
            # and combine it with '-branch'
            version_match = re.match(r'(\d+\.\d+)', self.pyramid_dist.version)
            if version_match is not None:
                pyramid_docs_branch = "%s-branch" % version_match.group()
            # if can not parse the version then default to 'latest'
            else:
                pyramid_docs_branch = 'latest'

        vars = {
            'project': project_name,
            'package': pkg_name,
            'egg': egg_name,
            'pyramid_version': pyramid_version,
            'pyramid_docs_branch': pyramid_docs_branch,
            }
        for scaffold_name in options.scaffold_name:
            for scaffold in self.scaffolds:
                if scaffold.name == scaffold_name:
                    scaffold.run(self, output_dir, vars)
        return 0

    def show_scaffolds(self):
        scaffolds = sorted(self.scaffolds, key=lambda x: x.name)
        if scaffolds:
            max_name = max([len(t.name) for t in scaffolds])
            self.out('Available scaffolds:')
            for scaffold in scaffolds:
                self.out('  %s:%s  %s' % (
                    scaffold.name,
                    ' '*(max_name-len(scaffold.name)), scaffold.summary))
        else:
            self.out('No scaffolds available')
        return 0

    def all_scaffolds(self):
        scaffolds = []
        eps = list(pkg_resources.iter_entry_points('pyramid.scaffold'))
        for entry in eps:
            try:
                scaffold_class = entry.load()
                scaffold = scaffold_class(entry.name)
                scaffolds.append(scaffold)
            except Exception as e: # pragma: no cover
                self.out('Warning: could not load entry point %s (%s: %s)' % (
                    entry.name, e.__class__.__name__, e))
        return scaffolds

    def out(self, msg): # pragma: no cover
        if not self.quiet:
            print(msg)

if __name__ == '__main__': # pragma: no cover
    sys.exit(main() or 0)
