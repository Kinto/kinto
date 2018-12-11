Getting started
###############

Installation
============

::

    $ pip install kinto

You can use *Kinto-Core* by doing ``import kinto.core`` in your application.

More details about installation and storage backend is provided in
:ref:`a dedicated section <install>`.


Start a Pyramid project
=======================

As detailed in `Pyramid documentation <http://docs.pylonsproject.org/projects/pyramid/>`_,
create a minimal application, or use its scaffolding tool:

::

    $ pcreate -s starter MyProject


Include Kinto-Core
------------------

In the application main file (e.g. :file:`MyProject/myproject/__init__.py`),
just add some extra initialization code:

.. code-block:: python
    :emphasize-lines: 3,6,7,13

    import pkg_resources

    import kinto.core
    from pyramid.config import Configurator

    # Module version, as defined in PEP-0396.
    __version__ = pkg_resources.get_distribution(__package__).version


    def main(global_config, **settings):
        config = Configurator(settings=settings)

        kinto.core.initialize(config, __version__, 'myproject')
        return config.make_wsgi_app()


By doing that, basic features like authentication, monitoring, error formatting,
deprecation indicators are now available, and rely on configuration present
in :file:`development.ini`.


Run!
----

With some backends, like *PostgreSQL*, some tables and indices have to be created.
A generic command is provided to accomplish this:

::

    $ kinto migrate --ini development.ini


Like any *Pyramid* application, it can be served locally with:

::

    $ pserve development.ini --reload

A *hello* view is now available at `http://localhost:6543/v0/ <http://localhost:6543/v0/>`_
(As well as basic endpoints like the :ref:`utilities <api-utilities>`).

The next steps will consist in building a custom application using :rtd:`Cornice <cornice>` or
**the Pyramid ecosystem**.

But most likely, it will consist in **defining REST resources** using *Kinto-Core*\ 's
Python API !


Authentication
--------------

Currently, if no :ref:`authentication is set in settings <configuration-authentication>`,
*Kinto-Core* relies on *Basic Auth*. It will associate a unique :term:`user id`
for every user/password combination.

Using `HTTPie <http://httpie.org>`_, it is as easy as:

::

    $ http -v http://localhost:6543/v0/ --auth user:pass

.. note::

    In the case of *Basic Auth*, there is no need of registering a user/password.
    Pick any combination, and include them in each request.


Define resources
================

In order to define a resource, inherit from :class:`kinto.core.resource.Resource`,
in a subclass, in :file:`myproject/views.py` for example:

.. code-block:: python

    from kinto.core import resource

    @resource.register()
    class Mushroom(resource.Resource):
        # No schema yet.
        pass

In application initialization, make *Pyramid* aware of it:

.. code-block:: python
    :emphasize-lines: 5

    def main(global_config, **settings):
        config = Configurator(settings=settings)

        kinto.core.initialize(config, __version__, 'myproject')
        config.scan("myproject.views")
        return config.make_wsgi_app()


In order to bypass the installation and configuration of *Redis* or *PostgreSQL*,
specify the «in-memory» backends in :file:`development.ini`:

.. code-block:: ini

    # development.ini
    myproject.cache_backend = kinto.core.cache.memory
    myproject.storage_backend = kinto.core.storage.memory
    myproject.permission_backend = kinto.core.permission.memory


A Mushroom resource API is now available at the ``/mushrooms/`` URL.

It will accept a bunch of REST operations (``GET``, ``POST``, ...).

The next step consists in attaching a schema to the resource, to control
what fields are accepted and stored.


Schema validation
-----------------

It is possible to validate records against a predefined schema, associated
to the resource.

Currently, only :rtd:`Colander <colander>` is supported, and it looks like this:


.. code-block:: python
    :emphasize-lines: 1,5,6,11

    import colander
    from kinto.core import resource


    class MushroomSchema(resource.ResourceSchema):
        name = colander.SchemaNode(colander.String())

        class Options:
            preserve_unknown = False  # Fails if field is unknown!


    @resource.register()
    class Mushroom(resource.Resource):
        schema = MushroomSchema


Enable middleware
=================

In order to enable WSGI middleware, wrap the application in the project ``main`` function:

.. code-block:: python
    :emphasize-lines: 6,7

    def main(global_config, **settings):
        config = Configurator(settings=settings)

        kinto.core.initialize(config, __version__, 'myproject')
        config.scan("myproject.views")
        app = config.make_wsgi_app()
        return kinto.install_middlewares(app, settings)


What's next ?
=============

Resource customization
----------------------

See :ref:`the resource documentation <resource>` to specify custom URLs,
schemaless resources, read-only fields, record pre-processing...


Advanced initialization
-----------------------

.. autofunction:: kinto.core.initialize


Beyond Kinto-Core
-----------------

*Kinto-Core* is just a component! The application can still be built and
extended using the full *Pyramid* ecosystem.
