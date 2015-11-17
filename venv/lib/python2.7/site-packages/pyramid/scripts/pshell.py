from code import interact
import optparse
import sys
import textwrap

from pyramid.compat import configparser
from pyramid.util import DottedNameResolver
from pyramid.paster import bootstrap

from pyramid.paster import setup_logging

from pyramid.scripts.common import parse_vars

def main(argv=sys.argv, quiet=False):
    command = PShellCommand(argv, quiet)
    return command.run()

class PShellCommand(object):
    usage = '%prog config_uri'
    description = """\
    Open an interactive shell with a Pyramid app loaded.  This command
    accepts one positional argument named "config_uri" which specifies the
    PasteDeploy config file to use for the interactive shell. The format is
    "inifile#name". If the name is left off, the Pyramid default application
    will be assumed.  Example: "pshell myapp.ini#main"

    If you do not point the loader directly at the section of the ini file
    containing your Pyramid application, the command will attempt to
    find the app for you. If you are loading a pipeline that contains more
    than one Pyramid application within it, the loader will use the
    last one.
    """
    bootstrap = (bootstrap,) # for testing

    parser = optparse.OptionParser(
        usage,
        description=textwrap.dedent(description)
        )
    parser.add_option('-p', '--python-shell',
                      action='store', type='string', dest='python_shell',
                      default='', help='ipython | bpython | python')
    parser.add_option('--setup',
                      dest='setup',
                      help=("A callable that will be passed the environment "
                            "before it is made available to the shell. This "
                            "option will override the 'setup' key in the "
                            "[pshell] ini section."))

    ConfigParser = configparser.ConfigParser # testing

    loaded_objects = {}
    object_help = {}
    setup = None

    def __init__(self, argv, quiet=False):
        self.quiet = quiet
        self.options, self.args = self.parser.parse_args(argv[1:])

    def pshell_file_config(self, filename):
        config = self.ConfigParser()
        config.read(filename)
        try:
            items = config.items('pshell')
        except configparser.NoSectionError:
            return

        resolver = DottedNameResolver(None)
        self.loaded_objects = {}
        self.object_help = {}
        self.setup = None
        for k, v in items:
            if k == 'setup':
                self.setup = v
            else:
                self.loaded_objects[k] = resolver.maybe_resolve(v)
                self.object_help[k] = v

    def out(self, msg): # pragma: no cover
        if not self.quiet:
            print(msg)

    def run(self, shell=None):
        if not self.args:
            self.out('Requires a config file argument')
            return 2
        config_uri = self.args[0]
        config_file = config_uri.split('#', 1)[0]
        setup_logging(config_file)
        self.pshell_file_config(config_file)

        # bootstrap the environ
        env = self.bootstrap[0](config_uri, options=parse_vars(self.args[1:]))

        # remove the closer from the env
        closer = env.pop('closer')

        # setup help text for default environment
        env_help = dict(env)
        env_help['app'] = 'The WSGI application.'
        env_help['root'] = 'Root of the default resource tree.'
        env_help['registry'] = 'Active Pyramid registry.'
        env_help['request'] = 'Active request object.'
        env_help['root_factory'] = (
            'Default root factory used to create `root`.')

        # override use_script with command-line options
        if self.options.setup:
            self.setup = self.options.setup

        if self.setup:
            # store the env before muddling it with the script
            orig_env = env.copy()

            # call the setup callable
            resolver = DottedNameResolver(None)
            setup = resolver.maybe_resolve(self.setup)
            setup(env)

            # remove any objects from default help that were overidden
            for k, v in env.items():
                if k not in orig_env or env[k] != orig_env[k]:
                    env_help[k] = v

        # load the pshell section of the ini file
        env.update(self.loaded_objects)

        # eliminate duplicates from env, allowing custom vars to override
        for k in self.loaded_objects:
            if k in env_help:
                del env_help[k]

        # generate help text
        help = ''
        if env_help:
            help += 'Environment:'
            for var in sorted(env_help.keys()):
                help += '\n  %-12s %s' % (var, env_help[var])

        if self.object_help:
            help += '\n\nCustom Variables:'
            for var in sorted(self.object_help.keys()):
                help += '\n  %-12s %s' % (var, self.object_help[var])

        if shell is None:
            shell = self.make_shell()

        try:
            shell(env, help)
        finally:
            closer()

    def make_shell(self):
        shell = None
        user_shell = self.options.python_shell.lower()
        if not user_shell:
            shell = self.make_ipython_shell()
            if shell is None:
                shell = self.make_bpython_shell()

        elif user_shell == 'ipython':
            shell = self.make_ipython_shell()

        elif user_shell == 'bpython':
            shell = self.make_bpython_shell()

        if shell is None:
            shell = self.make_default_shell()

        return shell

    def make_default_shell(self, interact=interact):
        def shell(env, help):
            cprt = 'Type "help" for more information.'
            banner = "Python %s on %s\n%s" % (sys.version, sys.platform, cprt)
            banner += '\n\n' + help + '\n'
            interact(banner, local=env)
        return shell

    def make_bpython_shell(self, BPShell=None):
        if BPShell is None: # pragma: no cover
            try:
                from bpython import embed
                BPShell = embed
            except ImportError:
                return None
        def shell(env, help):
            BPShell(locals_=env, banner=help + '\n')
        return shell

    def make_ipython_shell(self):
        shell = self.make_ipython_v1_1_shell()
        if shell is None:
            shell = self.make_ipython_v0_11_shell()
        if shell is None:
            shell = self.make_ipython_v0_10_shell()
        return shell

    def make_ipython_v1_1_shell(self, IPShellFactory=None):
        if IPShellFactory is None: # pragma: no cover
            try:
                from IPython.terminal.embed import (
                    InteractiveShellEmbed)
                IPShellFactory = InteractiveShellEmbed
            except ImportError:
                return None
        def shell(env, help):
            IPShell = IPShellFactory(banner2=help + '\n', user_ns=env)
            IPShell()
        return shell

    def make_ipython_v0_11_shell(self, IPShellFactory=None):
        if IPShellFactory is None: # pragma: no cover
            try:
                from IPython.frontend.terminal.embed import (
                    InteractiveShellEmbed)
                IPShellFactory = InteractiveShellEmbed
            except ImportError:
                return None
        def shell(env, help):
            IPShell = IPShellFactory(banner2=help + '\n', user_ns=env)
            IPShell()
        return shell

    def make_ipython_v0_10_shell(self, IPShellFactory=None):
        if IPShellFactory is None: # pragma: no cover
            try:
                from IPython.Shell import IPShellEmbed
                IPShellFactory = IPShellEmbed
            except ImportError:
                return None
        def shell(env, help):
            IPShell = IPShellFactory(argv=[], user_ns=env)
            IPShell.set_banner(IPShell.IP.BANNER + '\n' + help + '\n')
            IPShell()
        return shell

if __name__ == '__main__': # pragma: no cover
    sys.exit(main() or 0)
