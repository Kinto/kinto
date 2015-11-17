# (c) 2005 Ian Bicking and contributors; written for Paste
# (http://pythonpaste.org) Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
#
# For discussion of daemonizing:
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/278731
#
# Code taken also from QP: http://www.mems-exchange.org/software/qp/ From
# lib/site.py

import atexit
import ctypes
import errno
import logging
import optparse
import os
import re
import subprocess
import sys
import textwrap
import threading
import time
import traceback
import webbrowser

from paste.deploy import loadserver
from paste.deploy import loadapp
from paste.deploy.loadwsgi import loadcontext, SERVER

from pyramid.compat import PY3
from pyramid.compat import WIN

from pyramid.paster import setup_logging

from pyramid.scripts.common import parse_vars

MAXFD = 1024

try:
    import termios
except ImportError: # pragma: no cover
    termios = None

if WIN and not hasattr(os, 'kill'): # pragma: no cover
    # py 2.6 on windows
    def kill(pid, sig=None):
        """kill function for Win32"""
        # signal is ignored, semibogus raise message
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(1, 0, pid)
        if (0 == kernel32.TerminateProcess(handle, 0)):
            raise OSError('No such process %s' % pid)
else:
    kill = os.kill

def main(argv=sys.argv, quiet=False):
    command = PServeCommand(argv, quiet=quiet)
    return command.run()

class DaemonizeException(Exception):
    pass

class PServeCommand(object):

    usage = '%prog config_uri [start|stop|restart|status] [var=value]'
    description = """\
    This command serves a web application that uses a PasteDeploy
    configuration file for the server and application.

    If start/stop/restart is given, then --daemon is implied, and it will
    start (normal operation), stop (--stop-daemon), or do both.

    You can also include variable assignments like 'http_port=8080'
    and then use %(http_port)s in your config files.
    """
    default_verbosity = 1

    parser = optparse.OptionParser(
        usage,
        description=textwrap.dedent(description)
        )
    parser.add_option(
        '-n', '--app-name',
        dest='app_name',
        metavar='NAME',
        help="Load the named application (default main)")
    parser.add_option(
        '-s', '--server',
        dest='server',
        metavar='SERVER_TYPE',
        help="Use the named server.")
    parser.add_option(
        '--server-name',
        dest='server_name',
        metavar='SECTION_NAME',
        help=("Use the named server as defined in the configuration file "
              "(default: main)"))
    if hasattr(os, 'fork'):
        parser.add_option(
            '--daemon',
            dest="daemon",
            action="store_true",
            help="Run in daemon (background) mode")
    parser.add_option(
        '--pid-file',
        dest='pid_file',
        metavar='FILENAME',
        help=("Save PID to file (default to pyramid.pid if running in "
              "daemon mode)"))
    parser.add_option(
        '--log-file',
        dest='log_file',
        metavar='LOG_FILE',
        help="Save output to the given log file (redirects stdout)")
    parser.add_option(
        '--reload',
        dest='reload',
        action='store_true',
        help="Use auto-restart file monitor")
    parser.add_option(
        '--reload-interval',
        dest='reload_interval',
        default=1,
        help=("Seconds between checking files (low number can cause "
              "significant CPU usage)"))
    parser.add_option(
        '--monitor-restart',
        dest='monitor_restart',
        action='store_true',
        help="Auto-restart server if it dies")
    parser.add_option(
        '-b', '--browser',
        dest='browser',
        action='store_true',
        help="Open a web browser to server url")
    parser.add_option(
        '--status',
        action='store_true',
        dest='show_status',
        help="Show the status of the (presumably daemonized) server")
    parser.add_option(
        '-v', '--verbose',
        default=default_verbosity,
        dest='verbose',
        action='count',
        help="Set verbose level (default "+str(default_verbosity)+")")
    parser.add_option(
        '-q', '--quiet',
        action='store_const',
        const=0,
        dest='verbose',
        help="Suppress verbose output")

    if hasattr(os, 'setuid'):
        # I don't think these are available on Windows
        parser.add_option(
            '--user',
            dest='set_user',
            metavar="USERNAME",
            help="Set the user (usually only possible when run as root)")
        parser.add_option(
            '--group',
            dest='set_group',
            metavar="GROUP",
            help="Set the group (usually only possible when run as root)")

    parser.add_option(
        '--stop-daemon',
        dest='stop_daemon',
        action='store_true',
        help=('Stop a daemonized server (given a PID file, or default '
              'pyramid.pid file)'))

    _scheme_re = re.compile(r'^[a-z][a-z]+:', re.I)

    _reloader_environ_key = 'PYTHON_RELOADER_SHOULD_RUN'
    _monitor_environ_key = 'PASTE_MONITOR_SHOULD_RUN'

    possible_subcommands = ('start', 'stop', 'restart', 'status')

    def __init__(self, argv, quiet=False):
        self.options, self.args = self.parser.parse_args(argv[1:])
        if quiet:
            self.options.verbose = 0

    def out(self, msg): # pragma: no cover
        if self.options.verbose > 0:
            print(msg)

    def get_options(self):
        if (len(self.args) > 1
            and self.args[1] in self.possible_subcommands):
            restvars = self.args[2:]
        else:
            restvars = self.args[1:]

        return parse_vars(restvars)

    def run(self): # pragma: no cover
        if self.options.stop_daemon:
            return self.stop_daemon()

        if not hasattr(self.options, 'set_user'):
            # Windows case:
            self.options.set_user = self.options.set_group = None

        # @@: Is this the right stage to set the user at?
        self.change_user_group(
            self.options.set_user, self.options.set_group)

        if not self.args:
            self.out('You must give a config file')
            return 2
        app_spec = self.args[0]

        if (len(self.args) > 1
            and self.args[1] in self.possible_subcommands):
            cmd = self.args[1]
        else:
            cmd = None

        if self.options.reload:
            if os.environ.get(self._reloader_environ_key):
                if self.options.verbose > 1:
                    self.out('Running reloading file monitor')
                install_reloader(int(self.options.reload_interval), [app_spec])
                # if self.requires_config_file:
                #     watch_file(self.args[0])
            else:
                return self.restart_with_reloader()

        if cmd not in (None, 'start', 'stop', 'restart', 'status'):
            self.out(
                'Error: must give start|stop|restart (not %s)' % cmd)
            return 2

        if cmd == 'status' or self.options.show_status:
            return self.show_status()

        if cmd == 'restart' or cmd == 'stop':
            result = self.stop_daemon()
            if result:
                if cmd == 'restart':
                    self.out("Could not stop daemon; aborting")
                else:
                    self.out("Could not stop daemon")
                return result
            if cmd == 'stop':
                return result
            self.options.daemon = True

        if cmd == 'start':
            self.options.daemon = True

        app_name = self.options.app_name

        vars = self.get_options()

        if not self._scheme_re.search(app_spec):
            app_spec = 'config:' + app_spec
        server_name = self.options.server_name
        if self.options.server:
            server_spec = 'egg:pyramid'
            assert server_name is None
            server_name = self.options.server
        else:
            server_spec = app_spec
        base = os.getcwd()

        if getattr(self.options, 'daemon', False):
            if not self.options.pid_file:
                self.options.pid_file = 'pyramid.pid'
            if not self.options.log_file:
                self.options.log_file = 'pyramid.log'

        # Ensure the log file is writeable
        if self.options.log_file:
            try:
                writeable_log_file = open(self.options.log_file, 'a')
            except IOError as ioe:
                msg = 'Error: Unable to write to log file: %s' % ioe
                raise ValueError(msg)
            writeable_log_file.close()

        # Ensure the pid file is writeable
        if self.options.pid_file:
            try:
                writeable_pid_file = open(self.options.pid_file, 'a')
            except IOError as ioe:
                msg = 'Error: Unable to write to pid file: %s' % ioe
                raise ValueError(msg)
            writeable_pid_file.close()

        if getattr(self.options, 'daemon', False):
            try:
                self.daemonize()
            except DaemonizeException as ex:
                if self.options.verbose > 0:
                    self.out(str(ex))
                return 2

        if (self.options.monitor_restart
            and not os.environ.get(self._monitor_environ_key)):
            return self.restart_with_monitor()

        if self.options.pid_file:
            self.record_pid(self.options.pid_file)

        if self.options.log_file:
            stdout_log = LazyWriter(self.options.log_file, 'a')
            sys.stdout = stdout_log
            sys.stderr = stdout_log
            logging.basicConfig(stream=stdout_log)

        log_fn = app_spec
        if log_fn.startswith('config:'):
            log_fn = app_spec[len('config:'):]
        elif log_fn.startswith('egg:'):
            log_fn = None
        if log_fn:
            log_fn = os.path.join(base, log_fn)
            setup_logging(log_fn)

        server = self.loadserver(server_spec, name=server_name,
                                 relative_to=base, global_conf=vars)

        app = self.loadapp(app_spec, name=app_name, relative_to=base,
                global_conf=vars)

        if self.options.verbose > 0:
            if hasattr(os, 'getpid'):
                msg = 'Starting server in PID %i.' % os.getpid()
            else:
                msg = 'Starting server.'
            self.out(msg)

        def serve():
            try:
                server(app)
            except (SystemExit, KeyboardInterrupt) as e:
                if self.options.verbose > 1:
                    raise
                if str(e):
                    msg = ' ' + str(e)
                else:
                    msg = ''
                self.out('Exiting%s (-v to see traceback)' % msg)

        if self.options.browser:
            def open_browser():
                context = loadcontext(SERVER, app_spec, name=app_name, relative_to=base,
                        global_conf=vars)
                url = 'http://127.0.0.1:{port}/'.format(**context.config())
                time.sleep(1)
                webbrowser.open(url)
            t = threading.Thread(target=open_browser)
            t.setDaemon(True)
            t.start()

        serve()

    def loadapp(self, app_spec, name, relative_to, **kw): # pragma: no cover
        return loadapp(app_spec, name=name, relative_to=relative_to, **kw)

    def loadserver(self, server_spec, name, relative_to, **kw):# pragma:no cover
        return loadserver(
            server_spec, name=name, relative_to=relative_to, **kw)

    def quote_first_command_arg(self, arg): # pragma: no cover
        """
        There's a bug in Windows when running an executable that's
        located inside a path with a space in it.  This method handles
        that case, or on non-Windows systems or an executable with no
        spaces, it just leaves well enough alone.
        """
        if (sys.platform != 'win32' or ' ' not in arg):
            # Problem does not apply:
            return arg
        try:
            import win32api
        except ImportError:
            raise ValueError(
                "The executable %r contains a space, and in order to "
                "handle this issue you must have the win32api module "
                "installed" % arg)
        arg = win32api.GetShortPathName(arg)
        return arg

    def daemonize(self): # pragma: no cover
        pid = live_pidfile(self.options.pid_file)
        if pid:
            raise DaemonizeException(
                "Daemon is already running (PID: %s from PID file %s)"
                % (pid, self.options.pid_file))

        if self.options.verbose > 0:
            self.out('Entering daemon mode')
        pid = os.fork()
        if pid:
            # The forked process also has a handle on resources, so we
            # *don't* want proper termination of the process, we just
            # want to exit quick (which os._exit() does)
            os._exit(0)
        # Make this the session leader
        os.setsid()
        # Fork again for good measure!
        pid = os.fork()
        if pid:
            os._exit(0)

        # @@: Should we set the umask and cwd now?

        import resource  # Resource usage information.
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if (maxfd == resource.RLIM_INFINITY):
            maxfd = MAXFD
        # Iterate through and close all file descriptors.
        for fd in range(0, maxfd):
            try:
                os.close(fd)
            except OSError:  # ERROR, fd wasn't open to begin with (ignored)
                pass

        if (hasattr(os, "devnull")):
            REDIRECT_TO = os.devnull
        else:
            REDIRECT_TO = "/dev/null"
        os.open(REDIRECT_TO, os.O_RDWR)  # standard input (0)
        # Duplicate standard input to standard output and standard error.
        os.dup2(0, 1)  # standard output (1)
        os.dup2(0, 2)  # standard error (2)

    def _remove_pid_file(self, written_pid, filename, verbosity):
        current_pid = os.getpid()
        if written_pid != current_pid:
            # A forked process must be exiting, not the process that
            # wrote the PID file
            return
        if not os.path.exists(filename):
            return
        with open(filename) as f:
            content = f.read().strip()
        try:
            pid_in_file = int(content)
        except ValueError:
            pass
        else:
            if pid_in_file != current_pid:
                msg = "PID file %s contains %s, not expected PID %s"
                self.out(msg % (filename, pid_in_file, current_pid))
                return
        if verbosity > 0:
            self.out("Removing PID file %s" % filename)
        try:
            os.unlink(filename)
            return
        except OSError as e:
            # Record, but don't give traceback
            self.out("Cannot remove PID file: (%s)" % e)
        # well, at least lets not leave the invalid PID around...
        try:
            with open(filename, 'w') as f:
                f.write('')
        except OSError as e:
            self.out('Stale PID left in file: %s (%s)' % (filename, e))
        else:
            self.out('Stale PID removed')

    def record_pid(self, pid_file):
        pid = os.getpid()
        if self.options.verbose > 1:
            self.out('Writing PID %s to %s' % (pid, pid_file))
        with open(pid_file, 'w') as f:
            f.write(str(pid))
        atexit.register(self._remove_pid_file, pid, pid_file, self.options.verbose)

    def stop_daemon(self): # pragma: no cover
        pid_file = self.options.pid_file or 'pyramid.pid'
        if not os.path.exists(pid_file):
            self.out('No PID file exists in %s' % pid_file)
            return 1
        pid = read_pidfile(pid_file)
        if not pid:
            self.out("Not a valid PID file in %s" % pid_file)
            return 1
        pid = live_pidfile(pid_file)
        if not pid:
            self.out("PID in %s is not valid (deleting)" % pid_file)
            try:
                os.unlink(pid_file)
            except (OSError, IOError) as e:
                self.out("Could not delete: %s" % e)
                return 2
            return 1
        for j in range(10):
            if not live_pidfile(pid_file):
                break
            import signal
            kill(pid, signal.SIGTERM)
            time.sleep(1)
        else:
            self.out("failed to kill web process %s" % pid)
            return 3
        if os.path.exists(pid_file):
            os.unlink(pid_file)
        return 0

    def show_status(self): # pragma: no cover
        pid_file = self.options.pid_file or 'pyramid.pid'
        if not os.path.exists(pid_file):
            self.out('No PID file %s' % pid_file)
            return 1
        pid = read_pidfile(pid_file)
        if not pid:
            self.out('No PID in file %s' % pid_file)
            return 1
        pid = live_pidfile(pid_file)
        if not pid:
            self.out('PID %s in %s is not running' % (pid, pid_file))
            return 1
        self.out('Server running in PID %s' % pid)
        return 0

    def restart_with_reloader(self): # pragma: no cover
        self.restart_with_monitor(reloader=True)

    def restart_with_monitor(self, reloader=False): # pragma: no cover
        if self.options.verbose > 0:
            if reloader:
                self.out('Starting subprocess with file monitor')
            else:
                self.out('Starting subprocess with monitor parent')
        while 1:
            args = [self.quote_first_command_arg(sys.executable)] + sys.argv
            new_environ = os.environ.copy()
            if reloader:
                new_environ[self._reloader_environ_key] = 'true'
            else:
                new_environ[self._monitor_environ_key] = 'true'
            proc = None
            try:
                try:
                    _turn_sigterm_into_systemexit()
                    proc = subprocess.Popen(args, env=new_environ)
                    exit_code = proc.wait()
                    proc = None
                except KeyboardInterrupt:
                    self.out('^C caught in monitor process')
                    if self.options.verbose > 1:
                        raise
                    return 1
            finally:
                if proc is not None:
                    import signal
                    try:
                        kill(proc.pid, signal.SIGTERM)
                    except (OSError, IOError):
                        pass

            if reloader:
                # Reloader always exits with code 3; but if we are
                # a monitor, any exit code will restart
                if exit_code != 3:
                    return exit_code
            if self.options.verbose > 0:
                self.out('%s %s %s' % ('-' * 20, 'Restarting', '-' * 20))

    def change_user_group(self, user, group): # pragma: no cover
        if not user and not group:
            return
        import pwd, grp
        uid = gid = None
        if group:
            try:
                gid = int(group)
                group = grp.getgrgid(gid).gr_name
            except ValueError:
                import grp
                try:
                    entry = grp.getgrnam(group)
                except KeyError:
                    raise ValueError(
                        "Bad group: %r; no such group exists" % group)
                gid = entry.gr_gid
        try:
            uid = int(user)
            user = pwd.getpwuid(uid).pw_name
        except ValueError:
            try:
                entry = pwd.getpwnam(user)
            except KeyError:
                raise ValueError(
                    "Bad username: %r; no such user exists" % user)
            if not gid:
                gid = entry.pw_gid
            uid = entry.pw_uid
        if self.options.verbose > 0:
            self.out('Changing user to %s:%s (%s:%s)' % (
                user, group or '(unknown)', uid, gid))
        if gid:
            os.setgid(gid)
        if uid:
            os.setuid(uid)

class LazyWriter(object):

    """
    File-like object that opens a file lazily when it is first written
    to.
    """

    def __init__(self, filename, mode='w'):
        self.filename = filename
        self.fileobj = None
        self.lock = threading.Lock()
        self.mode = mode

    def open(self):
        if self.fileobj is None:
            with self.lock:
                self.fileobj = open(self.filename, self.mode)
        return self.fileobj

    def close(self):
        fileobj = self.fileobj
        if fileobj is not None:
            fileobj.close()

    def __del__(self):
        self.close()

    def write(self, text):
        fileobj = self.open()
        fileobj.write(text)
        fileobj.flush()

    def writelines(self, text):
        fileobj = self.open()
        fileobj.writelines(text)
        fileobj.flush()

    def flush(self):
        self.open().flush()

def live_pidfile(pidfile): # pragma: no cover
    """(pidfile:str) -> int | None
    Returns an int found in the named file, if there is one,
    and if there is a running process with that process id.
    Return None if no such process exists.
    """
    pid = read_pidfile(pidfile)
    if pid:
        try:
            kill(int(pid), 0)
            return pid
        except OSError as e:
            if e.errno == errno.EPERM:
                return pid
    return None

def read_pidfile(filename):
    if os.path.exists(filename):
        try:
            with open(filename) as f:
                content = f.read()
            return int(content.strip())
        except (ValueError, IOError):
            return None
    else:
        return None

def ensure_port_cleanup(
    bound_addresses, maxtries=30, sleeptime=2): # pragma: no cover
    """
    This makes sure any open ports are closed.

    Does this by connecting to them until they give connection
    refused.  Servers should call like::

        ensure_port_cleanup([80, 443])
    """
    atexit.register(_cleanup_ports, bound_addresses, maxtries=maxtries,
                    sleeptime=sleeptime)

def _cleanup_ports(
    bound_addresses, maxtries=30, sleeptime=2): # pragma: no cover
    # Wait for the server to bind to the port.
    import socket
    import errno
    for bound_address in bound_addresses:
        for attempt in range(maxtries):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(bound_address)
            except socket.error as e:
                if e.args[0] != errno.ECONNREFUSED:
                    raise
                break
            else:
                time.sleep(sleeptime)
        else:
            raise SystemExit('Timeout waiting for port.')
        sock.close()

def _turn_sigterm_into_systemexit(): # pragma: no cover
    """
    Attempts to turn a SIGTERM exception into a SystemExit exception.
    """
    try:
        import signal
    except ImportError:
        return
    def handle_term(signo, frame):
        raise SystemExit
    signal.signal(signal.SIGTERM, handle_term)

def ensure_echo_on(): # pragma: no cover
    if termios:
        fd = sys.stdin
        if fd.isatty():
            attr_list = termios.tcgetattr(fd)
            if not attr_list[3] & termios.ECHO:
                attr_list[3] |= termios.ECHO
                termios.tcsetattr(fd, termios.TCSANOW, attr_list)

def install_reloader(poll_interval=1, extra_files=None): # pragma: no cover
    """
    Install the reloading monitor.

    On some platforms server threads may not terminate when the main
    thread does, causing ports to remain open/locked.  The
    ``raise_keyboard_interrupt`` option creates a unignorable signal
    which causes the whole application to shut-down (rudely).
    """
    ensure_echo_on()
    mon = Monitor(poll_interval=poll_interval)
    if extra_files is None:
        extra_files = []
    mon.extra_files.extend(extra_files)
    t = threading.Thread(target=mon.periodic_reload)
    t.setDaemon(True)
    t.start()

class classinstancemethod(object):
    """
    Acts like a class method when called from a class, like an
    instance method when called by an instance.  The method should
    take two arguments, 'self' and 'cls'; one of these will be None
    depending on how the method was called.
    """

    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, obj, type=None):
        return _methodwrapper(self.func, obj=obj, type=type)

class _methodwrapper(object):

    def __init__(self, func, obj, type):
        self.func = func
        self.obj = obj
        self.type = type

    def __call__(self, *args, **kw):
        assert not 'self' in kw and not 'cls' in kw, (
            "You cannot use 'self' or 'cls' arguments to a "
            "classinstancemethod")
        return self.func(*((self.obj, self.type) + args), **kw)

class Monitor(object): # pragma: no cover
    """
    A file monitor and server restarter.

    Use this like:

    ..code-block:: Python

        install_reloader()

    Then make sure your server is installed with a shell script like::

        err=3
        while test "$err" -eq 3 ; do
            python server.py
            err="$?"
        done

    or is run from this .bat file (if you use Windows)::

        @echo off
        :repeat
            python server.py
        if %errorlevel% == 3 goto repeat

    or run a monitoring process in Python (``pserve --reload`` does
    this).  

    Use the ``watch_file(filename)`` function to cause a reload/restart for
    other non-Python files (e.g., configuration files).  If you have
    a dynamic set of files that grows over time you can use something like::

        def watch_config_files():
            return CONFIG_FILE_CACHE.keys()
        add_file_callback(watch_config_files)

    Then every time the reloader polls files it will call
    ``watch_config_files`` and check all the filenames it returns.
    """
    instances = []
    global_extra_files = []
    global_file_callbacks = []

    def __init__(self, poll_interval):
        self.module_mtimes = {}
        self.keep_running = True
        self.poll_interval = poll_interval
        self.extra_files = list(self.global_extra_files)
        self.instances.append(self)
        self.file_callbacks = list(self.global_file_callbacks)

    def _exit(self):
        # use os._exit() here and not sys.exit() since within a
        # thread sys.exit() just closes the given thread and
        # won't kill the process; note os._exit does not call
        # any atexit callbacks, nor does it do finally blocks,
        # flush open files, etc.  In otherwords, it is rude.
        os._exit(3)

    def periodic_reload(self):
        while True:
            if not self.check_reload():
                self._exit()
                break
            time.sleep(self.poll_interval)

    def check_reload(self):
        filenames = list(self.extra_files)
        for file_callback in self.file_callbacks:
            try:
                filenames.extend(file_callback())
            except:
                print(
                    "Error calling reloader callback %r:" % file_callback)
                traceback.print_exc()
        for module in list(sys.modules.values()):
            try:
                filename = module.__file__
            except (AttributeError, ImportError):
                continue
            if filename is not None:
                filenames.append(filename)
        for filename in filenames:
            try:
                stat = os.stat(filename)
                if stat:
                    mtime = stat.st_mtime
                else:
                    mtime = 0
            except (OSError, IOError):
                continue
            if filename.endswith('.pyc') and os.path.exists(filename[:-1]):
                mtime = max(os.stat(filename[:-1]).st_mtime, mtime)
            if not filename in self.module_mtimes:
                self.module_mtimes[filename] = mtime
            elif self.module_mtimes[filename] < mtime:
                print("%s changed; reloading..." % filename)
                return False
        return True

    def watch_file(self, cls, filename):
        """Watch the named file for changes"""
        filename = os.path.abspath(filename)
        if self is None:
            for instance in cls.instances:
                instance.watch_file(filename)
            cls.global_extra_files.append(filename)
        else:
            self.extra_files.append(filename)

    watch_file = classinstancemethod(watch_file)

    def add_file_callback(self, cls, callback):
        """Add a callback -- a function that takes no parameters -- that will
        return a list of filenames to watch for changes."""
        if self is None:
            for instance in cls.instances:
                instance.add_file_callback(callback)
            cls.global_file_callbacks.append(callback)
        else:
            self.file_callbacks.append(callback)

    add_file_callback = classinstancemethod(add_file_callback)

watch_file = Monitor.watch_file
add_file_callback = Monitor.add_file_callback

# For paste.deploy server instantiation (egg:pyramid#wsgiref)
def wsgiref_server_runner(wsgi_app, global_conf, **kw): # pragma: no cover
    from wsgiref.simple_server import make_server
    host = kw.get('host', '0.0.0.0')
    port = int(kw.get('port', 8080))
    server = make_server(host, port, wsgi_app)
    print('Starting HTTP server on http://%s:%s' % (host, port))
    server.serve_forever()

# For paste.deploy server instantiation (egg:pyramid#cherrypy)
def cherrypy_server_runner(
        app, global_conf=None, host='127.0.0.1', port=None,
        ssl_pem=None, protocol_version=None, numthreads=None,
        server_name=None, max=None, request_queue_size=None,
        timeout=None
        ): # pragma: no cover
    """
    Entry point for CherryPy's WSGI server

    Serves the specified WSGI app via CherryPyWSGIServer.

    ``app``

        The WSGI 'application callable'; multiple WSGI applications
        may be passed as (script_name, callable) pairs.

    ``host``

        This is the ipaddress to bind to (or a hostname if your
        nameserver is properly configured).  This defaults to
        127.0.0.1, which is not a public interface.

    ``port``

        The port to run on, defaults to 8080 for HTTP, or 4443 for
        HTTPS. This can be a string or an integer value.

    ``ssl_pem``

        This an optional SSL certificate file (via OpenSSL) You can
        generate a self-signed test PEM certificate file as follows:

            $ openssl genrsa 1024 > host.key
            $ chmod 400 host.key
            $ openssl req -new -x509 -nodes -sha1 -days 365  \\
                          -key host.key > host.cert
            $ cat host.cert host.key > host.pem
            $ chmod 400 host.pem

    ``protocol_version``

        The protocol used by the server, by default ``HTTP/1.1``.

    ``numthreads``

        The number of worker threads to create.

    ``server_name``

        The string to set for WSGI's SERVER_NAME environ entry.

    ``max``

        The maximum number of queued requests. (defaults to -1 = no
        limit).

    ``request_queue_size``

        The 'backlog' argument to socket.listen(); specifies the
        maximum number of queued connections.

    ``timeout``

        The timeout in seconds for accepted connections.
    """
    is_ssl = False
    if ssl_pem:
        port = port or 4443
        is_ssl = True

    if not port:
        if ':' in host:
            host, port = host.split(':', 1)
        else:
            port = 8080
    bind_addr = (host, int(port))

    kwargs = {}
    for var_name in ('numthreads', 'max', 'request_queue_size', 'timeout'):
        var = locals()[var_name]
        if var is not None:
            kwargs[var_name] = int(var)

    from cherrypy import wsgiserver

    server = wsgiserver.CherryPyWSGIServer(bind_addr, app,
                                           server_name=server_name, **kwargs)
    if ssl_pem is not None:
        if not PY3:
            server.ssl_certificate = server.ssl_private_key = ssl_pem
        else:
            # creates wsgiserver.ssl_builtin as side-effect
            wsgiserver.get_ssl_adapter_class()
            server.ssl_adapter = wsgiserver.ssl_builtin.BuiltinSSLAdapter(
                ssl_pem, ssl_pem)

    if protocol_version:
        server.protocol = protocol_version

    try:
        protocol = is_ssl and 'https' or 'http'
        if host == '0.0.0.0':
            print('serving on 0.0.0.0:%s view at %s://127.0.0.1:%s' %
                  (port, protocol, port))
        else:
            print('serving on %s://%s:%s' % (protocol, host, port))
        server.start()
    except (KeyboardInterrupt, SystemExit):
        server.stop()

    return server

if __name__ == '__main__': # pragma: no cover
    sys.exit(main() or 0)
