.. _openapi_spec:

OpenAPI Specification
#####################

The `OpenAPI Specification <https://github.com/OAI/OpenAPI-Specification>`_
(formally known as Swagger specification)
is a standard to describe REST APIs in a human and computer readable format
and allow several features like interactive documentation and automated
client generation.

GET /__api__
============

Returns the OpenAPI description for the running instance of Kinto on JSON format.

.. important::

    Getting the description from this endpoint is the only way to get the full
    description for the running instance. The description returned is based on a
    ``swagger.yaml`` valid OpenAPI description file on the root of the Kinto
    python package, but which lacks some instance specific definitions that
    are updated on runtime.


Known limitations
=================

OpenAPI 2.0 currently doesn't support some features that are present on Kinto API.
Some known limitations are:

#. Lack of validation on **OR** clauses (e.g. provide `data` or `permissions`
   in PATCH operations), which are trated as non-required on the description.
   This is more critical when setting
   `Batch operations <http://kinto.readthedocs.io/en/stable/api/1.x/batch.html>`_,
   which all the fields should be either defined on each request on the
   ``requests`` array or on the ``default`` object.

#. No support for :ref:`query filters <filtering>` on properties. Only named
   parameters are accepted on OpenAPI 2.0, so these are not included on the
   specification.

#. Optional response headers are not supported, as required for
   `Backoff signs <http://kinto.readthedocs.io/en/stable/api/1.x/backoff.html>`_.
   On the specification, the Backoff field is only listed as a response header
   on `default` responses, that should be raised with HTTP 5xx errors.

#. :ref:`Collection defined schemas <collection-json-schema>`
   fields are not validated because they accept any JSON Schema definition,
   which may be too complex to be handled by an OpenAPI description.
   Only the type of the field is checked as a valid JSON object.

.. important::

    The specifications used for loose schemas
    (objects that accept extra attributes of any type) include an
    ``additionalAttributes: {}`` definition that is not documented on the
    OpenAPI 2.0 Specification, but that allow loose schemas to be compatible
    with with several services created for OpenAPI/Swagger documented APIs,
    including code generators and interactive documentation renderers.


Interactive documentation
=========================

One way to interact and explore an API is through interactive documentation.
SwaggerUI is a resource that allows testing and visualizing the behavior
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
that the plugin provides or override the original definitions. The ``.yaml``
files provided are recursively merged in the order they are included
(the default description is always used first).

For example, if we want to include a plugin to our spec, we can use a description
as follows. The extensions are not required to be valid OpenAPI descriptions,
but they can be defined as such. You may also use references that are defined
on the base description.

.. code-block:: yaml

    swagger: 2.0
    paths:
      '/path/to/my/plugin':
        responses:
          '200':
            description: My plugin default response.
            schema:
              $ref: '#/definitions/MyPluginSchema'
          default:
            description: Default Kinto error.
            schema:
              $ref: '#/definitions/Error'

    definitions:
      MyPluginSchema:
        type: object


.. important::

    Extensions that change or include authentication methods may only overwrite
    the ``securityDefinitions`` field. The default security field (used when
    accessing API endpoints that require authentication) is updated on runtime
    to match the security definitions.
