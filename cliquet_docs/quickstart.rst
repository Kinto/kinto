Getting started
###############

Installation
============

::

    $ pip install cliquet


More details about installation and storage backend is provided in
:ref:`a dedicated section <installation>`.


Start a Pyramid project
=======================

As detailed in `Pyramid documentation <http://docs.pylonsproject.org/projects/pyramid/>`_,
create a minimal application, or use its scaffolding tool:

::

    $ pcreate -s starter MyProject


Include Cliquet
---------------

In the application main file (e.g. :file:`MyProject/myproject/__init__.py`),
just add some extra initialization code:

.. code-block:: python
    :emphasize-lines: 3,6,7,13

    import pkg_resources

    import cliquet
    from pyramid.config import Configurator

    # Module version, as defined in PEP-0396.
    __version__ = pkg_resources.get_distribution(__package__).version


    def main(global_config, **settings):
        config = Configurator(settings=settings)

        cliquet.initialize(config, __version__)
        return config.make_wsgi_app()


By doing that, basic features like authentication, monitoring, error formatting,
deprecation indicators are now available, and rely on configuration present
in :file:`development.ini`.


Run!
----

With some backends, like *PostgreSQL*, some tables and indices have to be created.
A generic command is provided to accomplish this:

::

    $ cliquet --ini development.ini migrate


Like any *Pyramid* application, it can be served locally with:

::

    $ pserve development.ini --reload

A *hello* view is now available at `http://localhost:6543/v0/ <http://localhost:6543/v0/>`_
(As well as basic endpoints like the :ref:`utilities <api-utilities>`).

The next steps will consist in building a custom application using :rtd:`Cornice <cornice>` or
**the Pyramid ecosystem**.

But most likely, it will consist in **defining REST resources** using *Cliquet*
python API !


Authentication
--------------

Currently, if no :ref:`authentication is set in settings <configuration-authentication>`,
*Cliquet* relies on *Basic Auth*. It will associate a unique :term:`user id`
for every user/password combination.

Using `HTTPie <http://httpie.org>`_, it is as easy as:

::

    $ http -v http://localhost:6543/v0/ --auth user:pass

.. note::

    In the case of *Basic Auth*, there is no need of registering a user/password.
    Pick any combination, and include them in each request.


Define resources
================

In order to define a resource, inherit from :class:`cliquet.resource.UserResource`,
in a subclass, in :file:`myproject/views.py` for example:

.. code-block:: python

    from cliquet import resource

    @resource.register()
    class Mushroom(resource.UserResource):
        # No schema yet.
        pass

In application initialization, make *Pyramid* aware of it:

.. code-block:: python
    :emphasize-lines: 5

    def main(global_config, **settings):
        config = Configurator(settings=settings)

        cliquet.initialize(config, __version__)
        config.scan("myproject.views")
        return config.make_wsgi_app()


In order to bypass the installation and configuration of *Redis* or *PostgreSQL*,
specify the «in-memory» backends in :file:`development.ini`:

.. code-block:: ini

    # development.ini
    cliquet.cache_backend = cliquet.cache.memory
    cliquet.storage_backend = cliquet.storage.memory
    cliquet.permission_backend = cliquet.permission.memory


A Mushroom resource API is now available at the ``/mushrooms/`` URL.

It will accept a bunch of REST operations, as defined in the :ref:`API section
<api-endpoints>`.

.. warning ::

    Without schema, a resource will not store any field at all!

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
    from cliquet import resource


    class MushroomSchema(resource.ResourceSchema):
        name = colander.SchemaNode(colander.String())


    @resource.register()
    class Mushroom(resource.UserResource):
        mapping = MushroomSchema()


What's next ?
=============

Configuration
-------------

See :ref:`configuration` to customize the application settings, such as
authentication, storage or cache backends.


Resource customization
----------------------

See :ref:`the resource documentation <resource>` to specify custom URLs,
schemaless resources, read-only fields, unicity constraints, record pre-processing...


Advanced initialization
-----------------------

.. autofunction:: cliquet.initialize


Beyond Cliquet
--------------

*Cliquet* is just a component! The application can still be built and
extended using the full *Pyramid* ecosystem.

See :ref:`the dedicated section <ecosystem>` for examples of *Cliquet* extensions.
