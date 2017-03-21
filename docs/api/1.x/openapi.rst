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
    description for the running instance. The description returned is based on
    the Service definitions and the configuration file.


Known limitations
=================

OpenAPI 2.0 currently doesn't support some features that are present on Kinto API.
Some known limitations are:

#. Lack of validation on **OR** clauses (e.g. provide `data` or `permissions`
   in PATCH operations), which are trated as non-required on the description.
   This is more critical when setting
   :ref:`Batch operations <batch>`,
   which all the fields should be either defined on each request on the
   ``requests`` array or on the ``default`` object.

#. No support for :ref:`query filters <filtering>` on properties. Only named
   parameters are accepted on OpenAPI 2.0, so these are not included on the
   specification.

#. Optional response headers are not supported, as required for
   :ref:`Backoff signs <backoff-indicators>`.

#. :ref:`Collection defined schemas <collection-json-schema>`
   fields are not validated because they accept any JSON Schema definition,
   which may be too complex to be handled by an OpenAPI description.
   Only the type of the field is checked as a valid JSON object.

#. Multiple schemas tagging different Content-Types for a same endpoint
   are not supported, so we don't document
   `JSON Patch operations <http://kinto.readthedocs.io/en/stable/api/1.x/records.html#json-patch-operations>`_.


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
accessing this
`Swagger UI example <http://petstore.swagger.io/?url=https://kinto.dev.mozaws.net/v1/__api__>`_

Automated client generation
===========================

We support clients from a few languages like JavaScript, Python and Java,
but if you need a client in a language that is currently not supported or
want to have your own personalized interface, you can speedup your development by using
`Swagger Code Generator <https://github.com/swagger-api/swagger-codegen>`_,
which generates standardized clients for APIs in more than 25 languages.

Improving the documentation
===========================

The Kinto OpenAPI description relies on
`Cornice Swagger <https://github.com/Cornices/cornice.ext.swagger>`_,
which is an extension for :rtd:`Cornice <cornice>` that extracts API
information from service definitions.
Cornice Swagger also needs some information that is not on the service such as
*Tags*, *Possible Responses* and *operation IDs*, so you may upgrade those
on the Kinto service definitions. Also you can contribute to Cornice Swagger directly.

Documenting your plugin
=======================

The current implementation supports extensions as follows:

- If the plugin defines views using Kinto or Cornice services, you can
  document it as a standard service as explained on the
  `Cornice Swagger documentation <https://cornices.github.io/cornice.ext.swagger/>`_.

- If the plugin changes the possible responses for a Resource, you can
  document it by subclassing :class:`kinto.core.resource.schema.ResourceReponses` and
  changing the ``responses`` attribute on your Resource ``ViewSet``.

- If the plugin adds an authentication method, you may declare it using
  :func:`kinto.core.openapi.OpenAPI.expose_authentication_method`.
