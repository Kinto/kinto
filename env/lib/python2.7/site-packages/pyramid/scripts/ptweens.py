import optparse
import sys
import textwrap

from pyramid.interfaces import ITweens

from pyramid.tweens import MAIN
from pyramid.tweens import INGRESS
from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

def main(argv=sys.argv, quiet=False):
    command = PTweensCommand(argv, quiet)
    return command.run()

class PTweensCommand(object):
    usage = '%prog config_uri'
    description = """\
    Print all implicit and explicit tween objects used by a Pyramid
    application.  The handler output includes whether the system is using an
    explicit tweens ordering (will be true when the "pyramid.tweens"
    deployment setting is used) or an implicit tweens ordering (will be true
    when the "pyramid.tweens" deployment setting is *not* used).

    This command accepts one positional argument named "config_uri" which
    specifies the PasteDeploy config file to use for the interactive
    shell. The format is "inifile#name". If the name is left off, "main"
    will be assumed.  Example: "ptweens myapp.ini#main".

    """
    parser = optparse.OptionParser(
        usage,
        description=textwrap.dedent(description),
        )

    stdout = sys.stdout
    bootstrap = (bootstrap,) # testing

    def __init__(self, argv, quiet=False):
        self.quiet = quiet
        self.options, self.args = self.parser.parse_args(argv[1:])

    def _get_tweens(self, registry):
        from pyramid.config import Configurator
        config = Configurator(registry=registry)
        return config.registry.queryUtility(ITweens)

    def out(self, msg): # pragma: no cover
        if not self.quiet:
            print(msg)

    def show_chain(self, chain):
        fmt = '%-10s  %-65s'
        self.out(fmt % ('Position', 'Name'))
        self.out(fmt % ('-' * len('Position'), '-' * len('Name')))
        self.out(fmt % ('-', INGRESS))
        for pos, (name, _) in enumerate(chain):
            self.out(fmt % (pos, name))
        self.out(fmt % ('-', MAIN))

    def run(self):
        if not self.args:
            self.out('Requires a config file argument')
            return 2
        config_uri = self.args[0]
        env = self.bootstrap[0](config_uri, options=parse_vars(self.args[1:]))
        registry = env['registry']
        tweens = self._get_tweens(registry)
        if tweens is not None:
            explicit = tweens.explicit
            if explicit:
                self.out('"pyramid.tweens" config value set '
                         '(explicitly ordered tweens used)')
                self.out('')
                self.out('Explicit Tween Chain (used)')
                self.out('')
                self.show_chain(tweens.explicit)
                self.out('')
                self.out('Implicit Tween Chain (not used)')
                self.out('')
                self.show_chain(tweens.implicit())
            else:
                self.out('"pyramid.tweens" config value NOT set '
                         '(implicitly ordered tweens used)')
                self.out('')
                self.out('Implicit Tween Chain')
                self.out('')
                self.show_chain(tweens.implicit())
        return 0

if __name__ == '__main__': # pragma: no cover
    sys.exit(main() or 0)
