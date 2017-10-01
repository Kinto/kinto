.. _FAQ:

FAQ
===

How does Kinto compare to other solutions?
-------------------------------------------

Before we started building our own data storage service, we took a look at what
was already out there. Our initial intent was to use and possibly extend
an existing community project rather than reinventing the wheel.

However, since none of the existing solutions we tried was a perfect fit for the
problems we needed to solve, notably regarding fine-grained permissions, we started
our own stack using the experience we gained from building Firefox Sync.

What follows is a comparison table showing how Kinto stacks up compared to some
other projects in this space.


===========================  ======  =============  ========  =======  ======= ==============  =======  =========
Project                      Kinto   Parse Server   Firebase  CouchDB  Kuzzle  Remote-Storage  Hoodie   BrowserFS
---------------------------  ------  -------------  --------  -------  ------- --------------  -------  ---------
Offline-first client         ✔       ✔              ✔         ✔        ✔       ✔               ✔
Fine-grained permissions     ✔       ✔              ✔                  ~                       [#]_
Easy query mechanism         ✔       ✔              ✔         [#]_     ✔       [#]_            ✔
Conflict resolution          ✔       ✔              ✔         ✔        ✔       ✔ [#]_          ✔
Validation                   ✔       ✔              ✔         ✔        ✔                       ✔
Revision history             ✔                                ✔                                ✔
File storage                 ✔       ✔                        ✔                ✔               ✔        ✔
Batch/bulk operations        ✔       ✔                        ✔        ✔                       ✔
Changes stream               ✔       ✔              ✔         ✔        ✔                       ✔
Pluggable authentication     ✔       ✔                        ✔                [#]_            ✔        ✔
Pluggable storage / cache    ✔       ✔                                         ✔
Self-hostable                ✔       ✔                        ✔        ✔       ✔               ✔        ✔
Decentralised discovery      [#]_                                              ✔
Open source                  ✔       ✔                        ✔        ✔       ✔               ✔        ✔
Language                     Python  Node.js                  Erlang   Node.js Node.js [#]_    Node.js  Node.js
===========================  ======  =============  ========  =======  ======= ==============  =======  =========

.. [#] Currently, user plugin in Hoodie auto-approves users, but they are working on it.
.. [#] CouchDB uses Map/Reduce as a query mechanism, which isn't easy to
       understand for newcomers.
.. [#] Remote Storage allows "ls" on a folder, but items are not sorted or
       paginated.
.. [#] Kinto uses the same mechanisms as Remote storage for conflict handling.
.. [#] Remote Storage supports OAuth2.0 implicit grant flow.
.. [#] Support for decentralised discovery
       `is planned <https://github.com/Kinto/kinto/issues/125>`_ but not
       implemented yet.
.. [#] Remote Storage doesn't define any default implementation (as it is
       a procol) but makes it easy to start with JavaScript and Node.js.

You can also read `a longer explanation of our choices and motivations behind the
creation of Kinto <http://www.servicedenuages.fr/en/generic-storage-ecosystem>`_
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
<http://www.servicedenuages.fr/en/kinto-encryption-example>`_.


Is there a package for my Operating System?
-------------------------------------------

No, but it's a great idea. Maintaining packages for several platforms is time-consuming
and we're a small team.

Currently we make sure it's :ref:`easy to run with Docker or Python pip <install>`.

We also have a :ref:`single-click deployment <deploy-an-instance>` on some cloud providers.

.. important::

    If you'd like to help us out by maintaining packages for your favourite OS,
    we'd be delighted to collaborate with you!


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

Yes, using the :github:`Kinto/kinto-attachment` plugin.


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

* :ref:`How to implement a custom authentication <tutorial-github>`
* :ref:`Kinto API documentation about authentication <authentication>`

.. note::

    We'd be delighted to add more built-in authentication methods into Kinto.
    Please reach out if you're interested!


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

Some helpers are provided in the :github:`Kinto/kinto.js` client. The three
provided conflict resolution strategies are:

* SERVER_WINS: local changes are overridden by remote ones ;
* CLIENT_WINS: remote changes are overridden by local ones ;
* MANUAL (default): handle them on your own.

Then there is, of course, a `convenient helper to handle conflict one by one
<https://kintojs.readthedocs.io/en/latest/api/#resolving-conflicts-manually>`_.


Would you recommend Redis or PostgreSQL?
----------------------------------------

You can use both of them:

* *Redis* is usually easier to install and run than PostgreSQL. But you will have a
  database running in memory which means your data should be smaller than your server RAM.
  *Redis* is great for the ``cache`` backend.

* *PostgreSQL* is the recommended backend for ``storage`` and ``permission`` in production.
  Mainly because data integrity is guaranteed, thanks to «per-request» transactions.
  It's also usually easier to backup and export data out of a PostgreSQL database.


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
