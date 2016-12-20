.. _openapi_spec:

OpenAPI Specification
#####################

The `OpenAPI Specification <https://github.com/OAI/OpenAPI-Specification>`_
(formally known as Swagger specification)
is a standard to describe REST APIs in a human and computer readable format
and allow several features like interactive documentation and automated
client generation.

.. important::
    OpenAPI 2.0 currently doensn't some features that are present on Kinto API.
    Some known limitations are
    lack of validation on or clauses (e.g. provide `data` or `permissions` in PATCH
    operations), no support for non schema querystrings, as used on :ref:`filtering <filtering>`
    with additional fields, and no optional response headers, as required for
    `Backoff signs`<http://kinto.readthedocs.io/en/stable/api/1.x/backoff.html>`.
    Also, :ref:`collection defined schemas <collection-json-schema>`,
    are not validated, So if you're using client
    generation, you may need to implement these features.

GET /swagger.json
=================

Returns the OpenAPI specification for the running instance of Kinto on JSON format.

Interactive documentation
=========================

One way to interact and explore an API is through interactive documentation.
SwaggerUI is a resource that allows testing and visualizing the behaviour
of an OpenAPI described interface.

You can try the instance running on https://kinto.dev.mozaws.net/v1/ from you browser
accessing `our example on SwaggerHub <https://app.swaggerhub.com/api/Kinto/kinto>`_

Automated client generation
===========================

We support clients from a few languages like JavaScript, Python and Java,
but if you need a client in a language that is currently not supported or
want to have your own personalized interface, you can speedup your development by using
`Swagger Code Generator <https://github.com/swagger-api/swagger-codegen>`_,
which generates standardized clients for APIs in more than 25 languages.

Using a custom specification
============================

The Kinto OpenAPI description relies on a ``kinto/swagger.yaml`` file.
You may replace the OpenAPI documentation for your deployment by providing a
``kinto.swagger_file`` entry on your configuration file.

OpenAPI extensions
==================

By default all includes on the configuration file will be prompt for a
``swagger.yaml`` file on the package root containing an OpenAPI extension
for the main specification. You may use it to include additional resources
that the plugin provides or override the original definitions. You may disable
Swagger extensions by setting ``kinto.swagger_extensions`` to ``False`` on the
configuration file.
