import binascii
import os
from textwrap import dedent

from pyramid.compat import native_

from pyramid.scaffolds.template import Template  # API

class PyramidTemplate(Template):
    """
     A class that can be used as a base class for Pyramid scaffolding
     templates.
    """
    def pre(self, command, output_dir, vars):
        """ Overrides :meth:`pyramid.scaffolds.template.Template.pre`, adding
        several variables to the default variables list (including
        ``random_string``, and ``package_logger``).  It also prevents common
        misnamings (such as naming a package "site" or naming a package
        logger "root".
        """
        vars['random_string'] = native_(binascii.hexlify(os.urandom(20)))
        package_logger = vars['package']
        if package_logger == 'root':
            # Rename the app logger in the rare case a project is named 'root'
            package_logger = 'app'
        vars['package_logger'] = package_logger
        return Template.pre(self, command, output_dir, vars)

    def post(self, command, output_dir, vars): # pragma: no cover
        """ Overrides :meth:`pyramid.scaffolds.template.Template.post`, to
        print "Welcome to Pyramid.  Sorry for the convenience." after a
        successful scaffolding rendering."""

        separator = "=" * 79
        msg = dedent(
            """
            %(separator)s
            Tutorials:     http://docs.pylonsproject.org/projects/pyramid_tutorials/en/latest/
            Documentation: http://docs.pylonsproject.org/projects/pyramid/en/latest/
            Twitter:       https://twitter.com/trypyramid
            Mailing List:  https://groups.google.com/forum/#!forum/pylons-discuss

            Welcome to Pyramid.  Sorry for the convenience.
            %(separator)s
        """ % {'separator': separator})

        self.out(msg)
        return Template.post(self, command, output_dir, vars)

    def out(self, msg): # pragma: no cover (replaceable testing hook)
        print(msg)

class StarterProjectTemplate(PyramidTemplate):
    _template_dir = 'starter'
    summary = 'Pyramid starter project using URL dispatch and Chameleon'

class ZODBProjectTemplate(PyramidTemplate):
    _template_dir = 'zodb'
    summary = 'Pyramid project using ZODB, traversal, and Chameleon'

class AlchemyProjectTemplate(PyramidTemplate):
    _template_dir = 'alchemy'
    summary = (
        'Pyramid project using SQLAlchemy, SQLite, URL dispatch, and '
        'Jinja2')
