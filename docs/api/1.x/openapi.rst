.. _openapi_spec:

OpenAPI Specification
#####################

The `OpenAPI Specification <https://github.com/OAI/OpenAPI-Specification>`_
(formally known as Swagger specification)
is a standard to describe REST APIs in a human and computer readable format
and allow several features like interactive documentation and automated
client generation.

.. important::
    OpenAPI 2.0 currently doensn't support schema free fields, so
    :ref:`collection defined schemas <collection-json-schema>`,
    :ref:`filtering <filtering>` and
    :ref:`selecting fields <selecting-fields>`
    are not supported by this documentation. If you're using client
    generation, you may have to implement these features.

GET /swagger.json
=================

Returns the OpenAPI specification for the running instance of Kinto using JSON format.
using the definitions from the file `swagger.json` on the package root.

Interactive documentation
=========================

.. replace Kinto acount on SwaggerHub and with SwaggerUI
   https://kinto.dev.mozaws.net/v1/ on when possible.


One way to interact and explore an API is through interactive documentation.
SwaggerUI is a resource that allows testing and visualizing the behaviour
of an OpenAPI described interface.

You can try the instance running on https://kinto.dev.mozaws.net/v1/ from you browser
accessing `our example on SwaggerHub <https://app.swaggerhub.com/api/gabisurita/kinto/1.13>`_
or `our example on Apiary <http://docs.kinto.apiary.io/>`.


Automated client generation
===========================

We support clients from a few languages like JavaScript, Python and Java,
but if you need a client in a language that we currently don't support or just want
to have your own personalized interface, you can speedup your development using
`Swagger Code Generator <https://github.com/swagger-api/swagger-codegen>`_,
which generates standardized clients for APIs in more than 25 languages.
