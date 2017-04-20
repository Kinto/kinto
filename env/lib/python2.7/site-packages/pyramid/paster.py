import os

from paste.deploy import (
    loadapp,
    appconfig,
    )

from pyramid.compat import configparser
from logging.config import fileConfig
from pyramid.scripting import prepare

def get_app(config_uri, name=None, options=None, loadapp=loadapp):
    """ Return the WSGI application named ``name`` in the PasteDeploy
    config file specified by ``config_uri``.

    ``options``, if passed, should be a dictionary used as variable assignments
    like ``{'http_port': 8080}``.  This is useful if e.g. ``%(http_port)s`` is
    used in the config file.

    If the ``name`` is None, this will attempt to parse the name from
    the ``config_uri`` string expecting the format ``inifile#name``.
    If no name is found, the name will default to "main"."""
    path, section = _getpathsec(config_uri, name)
    config_name = 'config:%s' % path
    here_dir = os.getcwd()

    app = loadapp(
        config_name,
        name=section,
        relative_to=here_dir,
        global_conf=options)

    return app

def get_appsettings(config_uri, name=None, options=None, appconfig=appconfig):
    """ Return a dictionary representing the key/value pairs in an ``app``
    section within the file represented by ``config_uri``.

    ``options``, if passed, should be a dictionary used as variable assignments
    like ``{'http_port': 8080}``.  This is useful if e.g. ``%(http_port)s`` is
    used in the config file.

    If the ``name`` is None, this will attempt to parse the name from
    the ``config_uri`` string expecting the format ``inifile#name``.
    If no name is found, the name will default to "main"."""
    path, section = _getpathsec(config_uri, name)
    config_name = 'config:%s' % path
    here_dir = os.getcwd()
    return appconfig(
        config_name,
        name=section,
        relative_to=here_dir,
        global_conf=options)

def setup_logging(config_uri, global_conf=None,
                  fileConfig=fileConfig,
                  configparser=configparser):
    """
    Set up logging via :func:`logging.config.fileConfig` with the filename
    specified via ``config_uri`` (a string in the form
    ``filename#sectionname``).

    ConfigParser defaults are specified for the special ``__file__``
    and ``here`` variables, similar to PasteDeploy config loading.
    Extra defaults can optionally be specified as a dict in ``global_conf``.
    """
    path, _ = _getpathsec(config_uri, None)
    parser = configparser.ConfigParser()
    parser.read([path])
    if parser.has_section('loggers'):
        config_file = os.path.abspath(path)
        full_global_conf = dict(
            __file__=config_file,
            here=os.path.dirname(config_file))
        if global_conf:
            full_global_conf.update(global_conf)
        return fileConfig(config_file, full_global_conf)

def _getpathsec(config_uri, name):
    if '#' in config_uri:
        path, section = config_uri.split('#', 1)
    else:
        path, section = config_uri, 'main'
    if name:
        section = name
    return path, section

def bootstrap(config_uri, request=None, options=None):
    """ Load a WSGI application from the PasteDeploy config file specified
    by ``config_uri``. The environment will be configured as if it is
    currently serving ``request``, leaving a natural environment in place
    to write scripts that can generate URLs and utilize renderers.

    This function returns a dictionary with ``app``, ``root``, ``closer``,
    ``request``, and ``registry`` keys.  ``app`` is the WSGI app loaded
    (based on the ``config_uri``), ``root`` is the traversal root resource
    of the Pyramid application, and ``closer`` is a parameterless callback
    that may be called when your script is complete (it pops a threadlocal
    stack).

    .. note::

       Most operations within :app:`Pyramid` expect to be invoked within the
       context of a WSGI request, thus it's important when loading your
       application to anchor it when executing scripts and other code that is
       not normally invoked during active WSGI requests.

    .. note::

       For a complex config file containing multiple :app:`Pyramid`
       applications, this function will setup the environment under the context
       of the last-loaded :app:`Pyramid` application. You may load a specific
       application yourself by using the lower-level functions
       :meth:`pyramid.paster.get_app` and :meth:`pyramid.scripting.prepare` in
       conjunction with :attr:`pyramid.config.global_registries`.

    ``config_uri`` -- specifies the PasteDeploy config file to use for the
    interactive shell. The format is ``inifile#name``. If the name is left
    off, ``main`` will be assumed.

    ``request`` -- specified to anchor the script to a given set of WSGI
    parameters. For example, most people would want to specify the host,
    scheme and port such that their script will generate URLs in relation
    to those parameters. A request with default parameters is constructed
    for you if none is provided. You can mutate the request's ``environ``
    later to setup a specific host/port/scheme/etc.

    ``options`` Is passed to get_app for use as variable assignments like 
    {'http_port': 8080} and then use %(http_port)s in the
    config file.

    See :ref:`writing_a_script` for more information about how to use this
    function.
    """
    app = get_app(config_uri, options=options)
    env = prepare(request)
    env['app'] = app
    return env

