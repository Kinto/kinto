Getting started
###############

Once storage engines and python dependencies have been installed, it's is
easy to get started!


Start a Pyramid project
=======================

As detailed in `Pyramid documentation <http://docs.pylonsproject.org/projects/pyramid/>`_,
create a minimal application, or use its scaffolding tool:

::

    pcreate -s starter MyProject


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


.. autofunction:: cliquet.initialize


By doing that, basic features like authentication, monitoring, error formatting,
deprecation are now available, as well as basic endpoints like the :ref:`utilities <api-utilities>`.

The next steps will consist in building a custom application using :rtd:`Cornice <cornice>` or
**the Pyramid ecosystem**.

But most likely, it will consist in defining resources using Cliquet API!


Configuration
=============

See :ref:`configuration` to customize the project settings,
such as the storage backend.

In order to get started quickly, and bypass the :term:`Firefox Accounts` setup,
the ``Basic Auth`` authentication can be enabled with:

.. code-block:: ini

    # myproject.ini
    cliquet.basic_auth_enabled = true

This will associate a unique :term:`user id` for every user/password combination.
Obviously, any authentication system can be activated, see :ref:`configuration-authentication`.


Define resources
================

In order to define a resource, just inherit from :class:`cliquet.resource.BaseResource`,
in :file:`project/views.py` for example:

.. code-block:: python

    from cliquet import resource

    @resource.crud()
    class Mushroom(resource.BaseResource):
        # missing schema
        pass

In application initialization, make Pyramid aware of it:

.. code-block:: python
    :emphasize-lines: 5

    def main(global_config, **settings):
        config = Configurator(settings=settings)

        cliquet.initialize(config, __version__)
        config.scan("project.views")
        return config.make_wsgi_app()


By doing that, a Mushroom resource API is now available at the ``/mushrooms/``
endpoint.

It will accept a bunch of REST operations, as defined in
the :ref:`API section <api-endpoints>`.

.. warning ::

    Without schema, a resource will not store any field at all!

The next step consists in defining what fields are accepted and stored.


Schema validation
-----------------

It is possible to validate records against a predefined schema, associated
to the resource.


.. code-block:: python
    :emphasize-lines: 1,5,6,11

    import colander
    from cliquet import resource


    class MushroomSchema(resource.ResourceSchema):
        name = colander.SchemaNode(colander.String())


    @resource.crud()
    class Mushroom(resource.BaseResource):
        mapping = MushroomSchema()


Advanced usage
--------------

See :ref:`the resource documentation <resource>`  to specify custom URLs,
schemaless resources, read-only fields, unicity constraints, record pre-processing...

