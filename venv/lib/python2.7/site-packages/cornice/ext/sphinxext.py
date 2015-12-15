# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# Contributors: Vincent Fretin
"""
Sphinx extension that is able to convert a service into a documentation.
"""
import sys
import json
from importlib import import_module
try:
    from importlib import reload
except ImportError:
    pass

from cornice.util import to_list, is_string, PY3
from cornice.service import get_services, clear_services

import docutils
from docutils import nodes, core
from docutils.parsers.rst import Directive, directives
from docutils.writers.html4css1 import Writer, HTMLTranslator
from sphinx.util.docfields import DocFieldTransformer

MODULES = {}


def convert_to_list(argument):
    """Convert a comma separated list into a list of python values"""
    if argument is None:
        return []
    else:
        return [i.strip() for i in argument.split(',')]


def convert_to_list_required(argument):
    if argument is None:
        raise ValueError('argument required but none supplied')
    return convert_to_list(argument)


class ServiceDirective(Directive):
    """ Service directive.

    Injects sections in the documentation about the services registered in the
    given module.

    Usage, in a sphinx documentation::

        .. cornice-autodoc::
            :modules: your.module
            :services: name1, name2
            :service: name1 # no need to specify both services and service.
            :ignore: a comma separated list of services names to ignore

    """
    has_content = True
    option_spec = {'modules': convert_to_list_required,
                   'service': directives.unchanged,
                   'services': convert_to_list,
                   'ignore': convert_to_list}
    domain = 'cornice'
    doc_field_types = []

    def __init__(self, *args, **kwargs):
        super(ServiceDirective, self).__init__(*args, **kwargs)
        self.env = self.state.document.settings.env

    def run(self):
        # clear the SERVICES variable, which will allow to use this
        # directive multiple times
        clear_services()

        # import the modules, which will populate the SERVICES variable.
        for module in self.options.get('modules'):
            if module in MODULES:
                reload(MODULES[module])
            else:
                MODULES[module] = import_module(module)

        names = self.options.get('services', [])

        service = self.options.get('service')
        if service is not None:
            names.append(service)

        # filter the services according to the options we got
        services = get_services(names=names or None,
                                exclude=self.options.get('exclude'))

        return [self._render_service(s) for s in services]

    def _render_service(self, service):
        service_id = "service-%d" % self.env.new_serialno('service')
        service_node = nodes.section(ids=[service_id])

        title = '%s service at %s' % (service.name.title(), service.path)
        service_node += nodes.title(text=title)

        if service.description is not None:
            service_node += rst2node(trim(service.description))

        for method, view, args in service.definitions:
            if method == 'HEAD':
                # Skip head - this is essentially duplicating the get docs.
                continue
            method_id = '%s-%s' % (service_id, method)
            method_node = nodes.section(ids=[method_id])
            method_node += nodes.title(text=method)

            if is_string(view):
                if 'klass' in args:
                    ob = args['klass']
                    view_ = getattr(ob, view.lower())
                    docstring = trim(view_.__doc__ or "") + '\n'
            else:
                docstring = trim(view.__doc__ or "") + '\n'

            if 'schema' in args:
                schema = args['schema']

                attrs_node = nodes.inline()
                for location in ('header', 'querystring', 'body'):
                    attributes = schema.get_attributes(location=location)
                    if attributes:
                        attrs_node += nodes.inline(
                            text='values in the %s' % location)
                        location_attrs = nodes.bullet_list()

                        for attr in attributes:
                            temp = nodes.list_item()

                            # Get attribute data-type
                            if hasattr(attr, 'type'):
                                attr_type = attr.type
                            elif hasattr(attr, 'typ'):
                                attr_type = attr.typ.__class__.__name__
                            else:
                                attr_type = None

                            temp += nodes.strong(text=attr.name)
                            if attr_type is not None:
                                temp += nodes.inline(text=' (%s)' % attr_type)
                            if not attr.required or attr.description:
                                temp += nodes.inline(text=' - ')
                                if not attr.required:
                                    if attr.missing is not None:
                                        default = json.dumps(attr.missing)
                                        temp += nodes.inline(
                                            text='(default: %s) ' % default)
                                    else:
                                        temp += nodes.inline(
                                            text='(optional) ')
                                if attr.description:
                                    temp += nodes.inline(text=attr.description)

                            location_attrs += temp

                        attrs_node += location_attrs
                method_node += attrs_node

            for validator in args.get('validators', ()):
                if validator.__doc__ is not None:
                    docstring += trim(validator.__doc__)

            if 'accept' in args:
                accept = to_list(args['accept'])

                if callable(accept):
                    if accept.__doc__ is not None:
                        docstring += accept.__doc__.strip()
                else:
                    accept_node = nodes.strong(text='Accepted content types:')
                    node_accept_list = nodes.bullet_list()
                    accept_node += node_accept_list

                    for item in accept:
                        temp = nodes.list_item()
                        temp += nodes.inline(text=item)
                        node_accept_list += temp

                    method_node += accept_node

            node = rst2node(docstring)
            DocFieldTransformer(self).transform_all(node)
            if node is not None:
                method_node += node

            renderer = args['renderer']
            if renderer == 'simplejson':
                renderer = 'json'

            response = nodes.paragraph()

            response += nodes.strong(text='Response: %s' % renderer)
            method_node += response

            service_node += method_node

        return service_node


# Utils


def trim(docstring):
    """
    Remove the tabs to spaces, and remove the extra spaces / tabs that are in
    front of the text in docstrings.

    Implementation taken from http://www.python.org/dev/peps/pep-0257/
    """
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    res = '\n'.join(trimmed)
    if not PY3 and not isinstance(res, unicode):
        res = res.decode('utf8')
    return res


class _HTMLFragmentTranslator(HTMLTranslator):
    def __init__(self, document):
        HTMLTranslator.__init__(self, document)
        self.head_prefix = ['', '', '', '', '']
        self.body_prefix = []
        self.body_suffix = []
        self.stylesheet = []

    def astext(self):
        return ''.join(self.body)


class _FragmentWriter(Writer):
    translator_class = _HTMLFragmentTranslator

    def apply_template(self):
        subs = self.interpolation_dict()
        return subs['body']


def rst2html(data):
    """Converts a reStructuredText into its HTML
    """
    if not data:
        return ''
    return core.publish_string(data, writer=_FragmentWriter())


class Env(object):
    temp_data = {}
    docname = ''


def rst2node(data):
    """Converts a reStructuredText into its node
    """
    if not data:
        return
    parser = docutils.parsers.rst.Parser()
    document = docutils.utils.new_document('<>')
    document.settings = docutils.frontend.OptionParser().get_default_values()
    document.settings.tab_width = 4
    document.settings.pep_references = False
    document.settings.rfc_references = False
    document.settings.env = Env()
    parser.parse(data, document)
    if len(document.children) == 1:
        return document.children[0]
    else:
        par = docutils.nodes.paragraph()
        for child in document.children:
            par += child
        return par


def setup(app):
    """Hook the directives when Sphinx ask for it."""
    app.add_directive('services', ServiceDirective)  # deprecated
    app.add_directive('cornice-autodoc', ServiceDirective)
