# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPBadRequest

from cornice import Service
from cornice.tests.support import CatchErrors
import json


service = Service(name="service", path="/service")


def has_payed(request):
    if 'paid' not in request.GET:
        request.errors.add('body', 'paid', 'You must pay!')


def foo_int(request):
    if 'foo' not in request.GET:
        return
    try:
        request.validated['foo'] = int(request.GET['foo'])
    except ValueError:
        request.errors.add('url', 'foo', 'Not an int')


@service.get(validators=(has_payed, foo_int))
def get1(request):
    res = {"test": "succeeded"}
    try:
        res['foo'] = request.validated['foo']
    except KeyError:
        pass

    return res


def _json(request):
    """The request body should be a JSON object."""
    try:
        request.validated['json'] = json.loads(request.body.decode('utf-8'))
    except ValueError:
        request.errors.add('body', 'json', 'Not a json body')


@service.post(validators=_json)
def post1(request):
    return {"body": request.body}


service2 = Service(name="service2", path="/service2")


@service2.get(accept=("application/json", "text/json"))
@service2.get(accept=("text/plain"), renderer="string")
def get2(request):
    return {"body": "yay!"}


service3 = Service(name="service3", path="/service3")


def _accept(request):
    return ('application/json', 'text/json')


@service3.get(accept=_accept)
def get3(request):
    return {"body": "yay!"}


def _filter(response):
    response.body = b"filtered response"
    return response

service4 = Service(name="service4", path="/service4")


def fail(request):
    request.errors.add('body', 'xml', 'Not XML')


def xml_error(errors):
    lines = ['<errors>']
    for error in errors:
        lines.append('<error>'
                     '<location>%(location)s</location>'
                     '<type>%(name)s</type>'
                     '<message>%(description)s</message>'
                     '</error>' % error)
    lines.append('</errors>')
    return HTTPBadRequest(body=''.join(lines))


@service4.post(validators=fail, error_handler=xml_error)
def post4(request):
    raise ValueError("Shouldn't get here")

# test filtered services
filtered_service = Service(name="filtered", path="/filtered", filters=_filter)


@filtered_service.get()
@filtered_service.post(exclude=_filter)
def get4(request):
    return "unfiltered"  # should be overwritten on GET

# test the "content_type" parameter (scalar)
service5 = Service(name="service5", path="/service5")


@service5.get()
@service5.post(content_type='application/json')
@service5.put(content_type=('text/plain', 'application/json'))
def post5(request):
    return "some response"

# test the "content_type" parameter (callable)
service6 = Service(name="service6", path="/service6")


def _content_type(request):
    return ('text/xml', 'application/json')


@service6.post(content_type=_content_type)
def post6(request):
    return {"body": "yay!"}

# test a mix of "accept" and "content_type" parameters
service7 = Service(name="service7", path="/service7")


@service7.post(accept='text/xml', content_type='application/json')
@service7.put(accept=('text/xml', 'text/plain'),
              content_type=('application/json', 'text/xml'))
def post7(request):
    return "some response"


try:
    from colander import (
        Invalid,
        MappingSchema,
        SequenceSchema,
        SchemaNode,
        String,
        Integer,
        Range,
        Email
    )
    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:
    def validate_bar(node, value):
        if value != 'open':
            raise Invalid(node, "The bar is not open.")

    class Integers(SequenceSchema):
        integer = SchemaNode(Integer(), type='int')

    class FooBarSchema(MappingSchema):
        # foo and bar are required, baz is optional
        foo = SchemaNode(String(), type='str')
        bar = SchemaNode(String(), type='str', validator=validate_bar)
        baz = SchemaNode(String(), type='str', missing=None)
        yeah = SchemaNode(String(), location="querystring", type='str')
        ipsum = SchemaNode(Integer(), type='int', missing=1,
                           validator=Range(0, 3))
        integers = Integers(location="body", type='list', missing=())

    foobar = Service(name="foobar", path="/foobar")
    foobaz = Service(name="foobaz", path="/foobaz")

    @foobar.post(schema=FooBarSchema)
    def foobar_post(request):
        return {"test": "succeeded"}

    custom_deserializer_service = Service(name="custom_deserializer_service",
                                          path="/custom_deserializer")

    def dummy_deserializer(request):
        values = request.body.decode().split(',')
        return dict(zip(['foo', 'bar', 'yeah'], values))

    @custom_deserializer_service.post(schema=FooBarSchema,
                                      deserializer=dummy_deserializer)
    def custom_deserializer_service_post(request):
        return {"test": "succeeded"}

    class StringSequence(SequenceSchema):
        _ = SchemaNode(String())

    class ListQuerystringSequence(MappingSchema):
        field = StringSequence(location="querystring")

    @foobaz.get(schema=ListQuerystringSequence)
    def foobaz_get(request):
        return {"field": request.validated['field']}

    class NewsletterSchema(MappingSchema):
        email = SchemaNode(String(), validator=Email())

    email_service = Service(name='newsletter', path='/newsletter')

    @email_service.post(schema=NewsletterSchema)
    def newsletter(request):
        return "ohyeah"


def includeme(config):
    config.include("cornice")
    config.scan("cornice.tests.validationapp")


def main(global_config, **settings):
    config = Configurator(settings={})
    config.include(includeme)
    return CatchErrors(config.make_wsgi_app())
