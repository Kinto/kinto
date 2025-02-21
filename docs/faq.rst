.. _FAQ:

FAQ
===

.. _compare-solutions:

How does Kinto compare to other solutions?
-------------------------------------------

*Kinto* was built in 2016. Back then, there were very few alternatives, and projects like `CouchDB <https://github.com/apache/couchdb>`_
did not have the fine-grained permissions we were looking for.

Over the years, many great (and better!) alternatives were created with more features for complex applications (e.g., built-in push notifications, or extensive analytics).

.. list-table:: :header-rows: 1

    * * Project
      * Description
    * * `RemoteStorage <https://remotestorage.io>`_
      * A free and open standard that enables users to host their own data and grant apps permission to access it. The ``remotestorage.js`` library and various server implementations allow for decentralized, user-centric data storage.
    * * `Supabase <https://supabase.com>`_
      * An open-source Firebase alternative built on PostgreSQL. It offers authentication, storage, real-time subscriptions, and APIs.
    * * `Appwrite <https://appwrite.io>`_
      * A self-hosted backend server providing authentication, databases, file storage, and more. Designed for web, mobile, and Flutter applications.
    * * `Nhost <https://nhost.io>`_
      * A full-stack serverless platform with a GraphQL API on top of PostgreSQL, including integrated authentication and storage.
    * * `Parse Platform <https://parseplatform.org>`_
      * The open-source version of the popular Parse backend. Offers user management, push notifications, and real-time data with Parse Server.
    * * `Hasura <https://hasura.io>`_
      * A GraphQL engine that provides real-time APIs and can be self-hosted. Works well alongside existing PostgreSQL databases.
    * * `Directus <https://directus.io>`_
      * A headless CMS that wraps any SQL database with a dynamic API and administration app. Fully open-source and self-hostable.
    * * `FeathersJS <https://feathersjs.com>`_
      * A lightweight, open-source REST and real-time API framework for Node.js. Can integrate with various databases and authentication providers.
    * * `Kuzzle <https://kuzzle.io/>`_
      * An open-source backend solution tailored for real-time applications and IoT. Provides multi-protocol support (including REST, MQTT, and WebSocket), an administration console, and plugin system.

.. note::

    You can read `a longer explanation of our choices and motivations behind the
    creation of Kinto
    <https://mozilla-services.github.io/servicedenuages.fr/en/generic-storage-ecosystem>`_
    on our blog.

Why the name «Kinto»?
---------------------

«*Kinto-Un*» is the name of the `flying nimbus of San Goku <http://dragonball.wikia.com/wiki/Flying_Nimbus>`_.
It is a small personal cloud, that flies at high speed and that you can share with
pure heart riders :)


I am seeing an Exception error, what's wrong?
---------------------------------------------

Have a look at the :ref:`Troubleshooting section <troubleshooting>` to
see what to do.


Can I encrypt my data?
----------------------

Kinto server stores any data you pass to it, whether it's encrypted or not. We believe
encryption should always be done on the client-side, and we make it `easy to use encryption in our Kinto.js client
<https://mozilla-services.github.io/servicedenuages.fr/en/kinto-encryption-example>`_.


Is there a package for my Operating System?
-------------------------------------------

No, but it's a great idea. Maintaining packages for several platforms is time-consuming
and we're a very small team.

Currently we make sure it's :ref:`easy to run with Docker or Python pip <install>`.


Why did you chose to use Python rather than X?
----------------------------------------------

We love `Python <https://python.org>`_ because it's a concise & expressive
language with powerful data structures & easy to learn,
so it was an obvious choice for the development team.

In addition, the Operations team at Mozilla is comfortable with deploying and
managing Python applications in production.

However, Python is just an implementation detail *per se*. Kinto is
defined by an HTTP API that could be implemented in any language.


Is it Web Scale?
----------------

YES™. Have a look at the ``/dev/null`` backend. ;-)


Can I store files inside Kinto?
-------------------------------

Yes, using the https://github.com/Kinto/kinto-attachment plugin.


I want to add business logic to Kinto!
--------------------------------------

By default, Kinto has no domain-specific logic. When we need some, we usually
start by :ref:`writing a plugin <tutorial-write-plugin>`.

Plugins can hook in many parts of the API. Events subscribers are the most frequently
used hooks, and allow you to perform extra checks or operations, or even raise HTTP
exceptions if necessary. Plugins can also add new URLs to the API etc.

If you eventually hit a point where you need even more logic on the server
side, you can build your own Kinto-esque service using the REST resources abstractions
from :ref:`kinto.core <kinto-core>`. In this way, your service will inherit all the best
practices and conventions that Kinto itself has, and you can seamlessly migrate.

Maybe Kinto is not what you need after all, :ref:`don't hesitate to start a conversation <community>`!


How does Kinto authenticate users?
-----------------------------------

Kinto authentication system is pluggable and controlled from settings.

By default it ships with a very simple (but limited) *Basic Authentication* policy, which
distinguishes users using the value provided in the header. In other words, any
combination of user:password will be accepted. Kinto will encrypt them and determine a
unique :term:`user id` from them.

See also:

* :ref:`Kinto API documentation about authentication <authentication>`


How to disable the permissions system (for development)?
--------------------------------------------------------

By default, only the creator of the object has permission to write into it.

During development, it can be convenient to give the permission to write to
any user.

Just create the bucket (or the collection) with ``system.Everyone`` in the
``write`` principals. For example, using ``httpie``:

.. code-block:: bash

    echo '{"permissions": {"write": ["system.Everyone"]}}' | \
        http PUT http://localhost:8888/v1/buckets/a-bucket --auth user:pass


If two users modify the same collection offline, how does that conflict get resolved?
-------------------------------------------------------------------------------------

When using :ref:`concurrency control <concurrency control>` request headers,
the conflicting operation will be rejected by the server.

The application developer can implement custom conflict resolution strategies,
using the :ref:`two versions of the object <error-responses-precondition>`,
or the :ref:`history of actions <api-history>` of that object.

Some helpers are provided in the https://github.com/Kinto/kinto.js client. The three
provided conflict resolution strategies are:

* SERVER_WINS: local changes are overridden by remote ones ;
* CLIENT_WINS: remote changes are overridden by local ones ;
* MANUAL (default): handle them on your own.

Then there is, of course, a `convenient helper to handle conflict one by one
<https://kintojs.readthedocs.io/en/latest/api/#resolving-conflicts-manually>`_.


Why PostgreSQL to store arbitrary JSON?
---------------------------------------

*Kinto* backends are pluggable.

We provide an implementation for PostgreSQL that relies on ``JSONB`` (version >=9.4).
It is very performant, allows sorting/filtering on arbitrary JSON fields, the
eco-system is rich and strong, and above all it is a rock-solid standard.

If you prefer MongoDB, RethinkDB or X, don't hesitate to start a storage, permission or
cache backend, we'll be delighted to give you a hand!


Why did you chose to use Pyramid rather than X?
-----------------------------------------------

Flask or Django Rest Framework could have been very good candidates!

We chose the Pyramid framework because we like `its flexibility and extensibility
<http://kinto.github.io/kinto-slides/2016.07.pybcn/index.html#slide25>`_.
Plus, we could :ref:`leverage Cornice helpers <technical-architecture>`, which
bring HTTP best practices out-of-the-box.


What about aggregation/reporting around data, is Kinto ready for that?
----------------------------------------------------------------------

This is not available from the main API — and probably never will.

However, this is something that can be done aside or on top of Kinto.

For example, you could use ElasticSearch. There is :ref:`tutorial for that <tutorial-write-plugin>`!

Also, if you use PostgreSQL for storage, you can create custom views in the database
that can be consumed for custom reporting.


Say I wanted to move all my Kinto data out of the database, would the best way to be via the backend?
-----------------------------------------------------------------------------------------------------

It really depends on how you setup things, and what kind of data is there. One really
simple way is to use the HTTP API.  But depending the access you have to the user's data,
it might or might not be the solution you're looking for. If you have access to the
server, then  doing a dump would get you the data out, but it won't be in any documented
format (it will be in an internal representation).

Nevertheless you can use the Kinto HTTP API to sync two databases.
