# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import inspect
import warnings


def _generate_colander_validator(location):
    """
    Generate a colander validator for data from the given location.

    :param location: The location in the request to find the data to be
        validated, such as "body" or "querystring".
    :type location: str
    :return: Returns a callable that will validate the request at the given
        location.
    :rtype: callable
    """

    def _validator(request, schema=None, deserializer=None, **kwargs):
        """
        Validate the location against the schema defined on the service.

        The content of the location is deserialized, validated and stored in
        the ``request.validated`` attribute.

        .. note::

            If no schema is defined, this validator does nothing.
            Schema should be of type :class:`~colander:colander.MappingSchema`.

        :param request: Current request
        :type request: :class:`~pyramid:pyramid.request.Request`

        :param schema: The Colander schema
        :param deserializer: Optional deserializer, defaults to
            :func:`cornice.validators.extract_cstruct`
        """
        import colander

        if schema is None:
            return

        schema_instance = _ensure_instantiated(schema)

        if not isinstance(schema_instance, colander.MappingSchema):
            raise TypeError("Schema should inherit from colander.MappingSchema.")

        class RequestSchemaMeta(colander._SchemaMeta):
            """
            A metaclass that will inject a location class attribute into
            RequestSchema.
            """

            def __new__(cls, name, bases, class_attrs):
                """
                Instantiate the RequestSchema class.

                :param name: The name of the class we are instantiating. Will
                    be "RequestSchema".
                :type name: str
                :param bases: The class's superclasses.
                :type bases: tuple
                :param dct: The class's class attributes.
                :type dct: dict
                """
                class_attrs[location] = schema_instance
                return type(name, bases, class_attrs)

        class RequestSchema(colander.MappingSchema, metaclass=RequestSchemaMeta):  # noqa
            """A schema to validate the request's location attributes."""

            pass

        validator(request, RequestSchema(), deserializer, **kwargs)
        validated_location = request.validated.get(location, {})
        request.validated.update(validated_location)
        if location not in validated_location:
            request.validated.pop(location, None)

    return _validator


body_validator = _generate_colander_validator("body")
headers_validator = _generate_colander_validator("headers")
path_validator = _generate_colander_validator("path")
querystring_validator = _generate_colander_validator("querystring")


def validator(request, schema=None, deserializer=None, **kwargs):
    """
    Validate the full request against the schema defined on the service.

    Each attribute of the request is deserialized, validated and stored in the
    ``request.validated`` attribute
    (eg. body in ``request.validated['body']``).

    .. note::

        If no schema is defined, this validator does nothing.

    :param request: Current request
    :type request: :class:`~pyramid:pyramid.request.Request`

    :param schema: The Colander schema
    :param deserializer: Optional deserializer, defaults to
        :func:`cornice.validators.extract_cstruct`
    """
    import colander

    from kinto.core.cornice.validators import extract_cstruct

    if deserializer is None:
        deserializer = extract_cstruct

    if schema is None:
        return

    schema = _ensure_instantiated(schema)
    cstruct = deserializer(request)
    try:
        deserialized = schema.deserialize(cstruct)
    except colander.Invalid as e:
        translate = request.localizer.translate
        error_dict = e.asdict(translate=translate)
        for name, msg in error_dict.items():
            location, _, field = name.partition(".")
            request.errors.add(location, field, msg)
    else:
        request.validated.update(deserialized)


def _ensure_instantiated(schema):
    if inspect.isclass(schema):
        warnings.warn(
            "Setting schema to a class is deprecated. Set schema to an instance instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        schema = schema()
    return schema
