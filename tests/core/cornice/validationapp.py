# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import json

from colander import (
    Email,
    Integer,
    Invalid,
    MappingSchema,
    Range,
    SchemaNode,
    SequenceSchema,
    String,
    deferred,
    drop,
    null,
)
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPBadRequest

from kinto.core.cornice import Service
from kinto.core.cornice.validators import colander_validator

from .support import CatchErrors


# Service for testing callback-based validators.
service = Service(name="service", path="/service")


def has_payed(request, **kw):
    if "paid" not in request.GET:
        request.errors.add("body", "paid", "You must pay!")


def foo_int(request, **kw):
    if "foo" not in request.GET:
        return
    try:
        request.validated["foo"] = int(request.GET["foo"])
    except ValueError:
        request.errors.add("url", "foo", "Not an int")


@service.get(validators=(has_payed, foo_int))
def get1(request):
    res = {"test": "succeeded"}
    try:
        res["foo"] = request.validated["foo"]
    except KeyError:
        pass

    return res


def _json(request, **kw):
    """The request body should be a JSON object."""
    try:
        request.validated["json"] = json.loads(request.body.decode("utf-8"))
    except ValueError:
        request.errors.add("body", "json", "Not a json body")


@service.post(validators=_json)
def post1(request):
    return {"body": request.body}


# Service for testing the "accept" parameter (scalar and list).
service2 = Service(name="service2", path="/service2")


@service2.get(accept=("application/json"))
@service2.get(accept=("text/plain"), renderer="string")
def get2(request):
    return {"body": "yay!"}


# Service for testing the "accept" parameter (callable).
service3 = Service(name="service3", path="/service3")


@service3.get(accept=lambda request: ("application/json", "text/plain"))
@service3.put(accept=lambda request: ("application/json", "text/plain"))
def get3(request):
    return {"body": "yay!"}


service4 = Service(name="service4", path="/service4")


def fail(request, **kw):
    request.errors.add("body", "xml", "Not XML")


def xml_error(request):
    errors = request.errors
    lines = ["<errors>"]
    for error in errors:
        lines.append(
            "<error>"
            "<location>%(location)s</location>"
            "<type>%(name)s</type>"
            "<message>%(description)s</message>"
            "</error>" % error
        )
    lines.append("</errors>")
    return HTTPBadRequest(body="".join(lines))


@service4.post(validators=fail, error_handler=xml_error)
def post4(request):
    raise ValueError("Shouldn't get here")


# Service for testing the "content_type" parameter (scalar and list).
service5 = Service(name="service5", path="/service5")


@service5.get()
@service5.post(content_type="application/json")
@service5.put(content_type=("text/plain", "application/json"))
def post5(request):
    return "some response"


# Service for testing the "content_type" parameter (callable).
service6 = Service(name="service6", path="/service6")


@service6.post(content_type=lambda request: ("text/xml", "application/json"))
@service6.put(content_type=lambda request: "text/xml")
def post6(request):
    return {"body": "yay!"}


# Service for testing a mix of "accept" and "content_type" parameters.
service7 = Service(name="service7", path="/service7")


@service7.post(accept="text/xml", content_type="application/json")
@service7.put(accept=("text/xml", "text/plain"), content_type=("application/json", "text/xml"))
def post7(request):
    return "some response"


# services for colander validation
signup = Service(name="signup", path="/signup")
bound = Service(name="bound", path="/bound")
group_signup = Service(name="group signup", path="/group_signup")
body_group_signup = Service(name="body_group signup", path="/body_group_signup")
body_signup = Service(name="body signup", path="/body_signup")
foobar = Service(name="foobar", path="/foobar")
foobaz = Service(name="foobaz", path="/foobaz")
email_service = Service(name="newsletter", path="/newsletter")
item_service = Service(name="item", path="/item/{item_id}")
form_service = Service(name="form", path="/form")


class SignupSchema(MappingSchema):
    username = SchemaNode(String())


@deferred
def deferred_missing(node, kw):
    import random

    return kw.get("missing_foo") or random.random()


class NeedsBindingSchema(MappingSchema):
    somefield = SchemaNode(String(), missing=deferred_missing)


def rebinding_validator(request, **kwargs):
    kwargs["schema"] = NeedsBindingSchema().bind()
    return colander_validator(request, **kwargs)


@bound.post(schema=NeedsBindingSchema().bind(), validators=(rebinding_validator,))
def bound_post(request):
    return request.validated


@bound.post(
    schema=NeedsBindingSchema().bind(missing_foo=-10),
    validators=(colander_validator,),
    header="X-foo",
)
def bound_post_with_override(request):
    return request.validated


@signup.post(schema=SignupSchema(), validators=(colander_validator,))
def signup_post(request):
    return request.validated


class GroupSignupSchema(SequenceSchema):
    user = SignupSchema()


@group_signup.post(schema=GroupSignupSchema(), validators=(colander_validator,))
def group_signup_post(request):
    return {"data": request.validated}


class BodyGroupSignupSchema(MappingSchema):
    body = GroupSignupSchema()


@body_group_signup.post(schema=BodyGroupSignupSchema(), validators=(colander_validator,))
def body_group_signup_post(request):
    return {"data": request.validated["body"]}


class BodySignupSchema(MappingSchema):
    body = SignupSchema()


@body_signup.post(schema=BodySignupSchema(), validators=(colander_validator,))
def body_signup_post(request):
    return {"data": request.validated}


def validate_bar(node, value, **kwargs):
    if value != "open":
        raise Invalid(node, "The bar is not open.")


class Integers(SequenceSchema):
    integer = SchemaNode(Integer(), type="int")


class BodySchema(MappingSchema):
    # foo and bar are required, baz is optional
    foo = SchemaNode(String())
    bar = SchemaNode(String(), validator=validate_bar)
    baz = SchemaNode(String(), missing=None)
    ipsum = SchemaNode(Integer(), missing=1, validator=Range(0, 3))
    integers = Integers(missing=())


class Query(MappingSchema):
    yeah = SchemaNode(String(), type="str")


class RequestSchema(MappingSchema):
    body = BodySchema()
    querystring = Query()

    def deserialize(self, cstruct):
        if "body" in cstruct and cstruct["body"] == b"hello,open,yeah":
            values = cstruct["body"].decode().split(",")
            cstruct["body"] = dict(zip(["foo", "bar", "yeah"], values))

        return MappingSchema.deserialize(self, cstruct)


@foobar.post(schema=RequestSchema(), validators=(colander_validator,))
def foobar_post(request):
    return {"test": "succeeded"}


class StringSequence(SequenceSchema):
    _ = SchemaNode(String())


class ListQuerystringSequence(MappingSchema):
    field = StringSequence()

    def deserialize(self, cstruct):
        if "field" in cstruct and not isinstance(cstruct["field"], list):
            cstruct["field"] = [cstruct["field"]]
        return MappingSchema.deserialize(self, cstruct)


class QSSchema(MappingSchema):
    querystring = ListQuerystringSequence()


@foobaz.get(schema=QSSchema(), validators=(colander_validator,))
def foobaz_get(request):
    return {"field": request.validated["querystring"]["field"]}


class NewsletterSchema(MappingSchema):
    email = SchemaNode(String(), validator=Email(), missing=drop)


class RefererSchema(MappingSchema):
    ref = SchemaNode(Integer(), missing=drop)


class NewsletterPayload(MappingSchema):
    body = NewsletterSchema()
    querystring = RefererSchema()

    def deserialize(self, cstruct=null):
        appstruct = super(NewsletterPayload, self).deserialize(cstruct)
        email = appstruct["body"].get("email")
        ref = appstruct["querystring"].get("ref")
        if email and ref and len(email) != ref:
            body_node, _ = self.children
            exc = Invalid(body_node)
            exc["email"] = "Invalid email length"
            raise exc
        return appstruct


@email_service.post(schema=NewsletterPayload(), validators=(colander_validator,))
def newsletter(request):
    return request.validated


class ItemPathSchema(MappingSchema):
    item_id = SchemaNode(Integer())


class ItemSchema(MappingSchema):
    path = ItemPathSchema()


@item_service.get(schema=ItemSchema(), validators=(colander_validator,))
def item(request):
    return request.validated["path"]


class FormSchema(MappingSchema):
    field1 = SchemaNode(String())
    field2 = SchemaNode(String())


@form_service.post(schema=FormSchema(), validators=(colander_validator,))
def form(request):
    return request.validated


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include("kinto.core.cornice")
    config.scan("tests.core.cornice.validationapp")
    # used for simulating pyramid session object access in validators
    config.add_request_method(lambda x: "secret", "get_csrf")
    return CatchErrors(config.make_wsgi_app())
