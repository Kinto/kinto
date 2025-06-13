# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


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
