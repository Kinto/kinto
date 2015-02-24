Getting started
###############

Once storage engines and python dependencies have been installed, it's is
easy to get started!


Start a Pyramid project
=======================

As detailed in `Pyramid documentation <http://docs.pylonsproject.org/projects/pyramid/>`_,
create a minimal application, or use its scaffolding tool:

    pcreate -s starter MyProject


Include Cliquet
---------------

In the application main file (e.g. :file:`MyProject/myproject/__init__.py`),
just add some extra initialization code:

.. code-block :: python

    import pkg_resources

    import cliquet
    from pyramid.config import Configurator

    # Module version, as defined in PEP-0396.
    __version__ = pkg_resources.get_distribution(__package__).version


    def main(global_config, **settings):
        config = Configurator(settings=settings)

        cliquet.initialize_cliquet(config, __version__)

        return config.make_wsgi_app()


By doing that, basic endpoints are now available, as defined in
the :ref:`API section <api-endpoints>`.


Configuration
=============

See :ref:`configuration`_ documentation to customize the project settings,
such as the storage backend.

In order to bypass Firefox Account setup, a ``Basic Auth`` authentication can be
be enabled with::

    cliquet.basic_auth_backdoor = true

This will associate a unique :term:`user id` for every user/password combination.


Define resources
================

In order to define a resource, just inherit from :class:`cliquet.resource.BaseResource`,
in :file:`project/views.py` for example:

.. code-block :: python

    from cliquet import resource

    @resource.crud()
    class Mushroom(resource.BaseResource):
        pass


In application initialization, make Pyramid aware of it:

.. code-block :: python

    initialize_cliquet(config, __version__)
    config.scan("project.views")


By doing that, a Mushroom resource is now available at the `/mushrooms/` endpoint.

It will accept a bunch of REST operations, as defined in
the :ref:`API section <api-endpoints>`.


Schema validation
-----------------

It is possible to validate records against a predefined schema, associated
to the resource.


.. code-block :: python

    import colander
    from cliquet import resource


    class MushroomSchema(resource.ResourceSchema):
        name = colander.SchemaNode(colander.String())


    @resource.crud()
    class Mushroom(resource.BaseResource):
        mapping = MushroomSchema()


Advanced usage
--------------

See :ref:`resource-class`_ documentation to specify read-only fields,
unicity constraints or record pre-processing...
