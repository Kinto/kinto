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


===========================  ======  ======  ========  =======  ======= ==============  =======  =========
Project                      Kinto   Parse   Firebase  CouchDB  Kuzzle  Remote-Storage  Hoodie   BrowserFS
---------------------------  ------  ------  --------  -------  ------- --------------  -------  ---------
Offline-first client         ✔       ✔       ✔         ✔        ✔       ✔               ✔
Fine-grained permissions     ✔       ✔       ✔                  ~                       [#]_
Easy query mechanism         ✔       ✔       ✔         [#]_     ✔       [#]_            ✔
Conflict resolution          ✔       ✔       ✔         ✔        ✔       ✔ [#]_          ✔
Validation                   ✔       ✔       ✔         ✔        ✔                       ✔
Revision history                                       ✔                                ✔
File storage                 ✔       ✔                 ✔                ✔               ✔        ✔
Batch/bulk operations        ✔       ✔                 ✔        ✔                       ✔
Changes stream               ✔       ✔       ✔         ✔        ✔                       ✔
Pluggable authentication     ✔                         ✔                [#]_            ✔        ✔
Pluggable storage / cache    ✔                                          ✔
Self-hostable                ✔       ✔                 ✔        ✔       ✔               ✔        ✔
Decentralised discovery      [#]_                                       ✔
Open source                  ✔       ✔                 ✔        ✔       ✔               ✔        ✔
Language                     Python                    Erlang   Node.js Node.js [#]_    Node.js  Node.js
===========================  ======  ======  ========  =======  ======= ==============  =======  =========

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
defined by an HTTP protocol that could be implemented in any language.


Is it Web Scale?
----------------

YES™. Have a look at the ``/dev/null`` backend. ;-)


Can I store files inside Kinto?
-------------------------------

Yes, using the :github:`Kinto/kinto-attachment` plugin.


I want to add business logic to Kinto!
--------------------------------------

We recommend that when you're starting to build a Kinto-based
application, you use Kinto as the back-end. You can use existing Kinto
libraries to get up and running quickly.

If you eventually hit a point where you need more logic on the server
side, you can build your own Kinto-esque service using the library in
``kinto.core``. In this way, your service will inherit all the best
practices and conventions that Kinto itself has, and you can
seamlessly migrate.

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
``write`` principals:

.. code-block:: bash

    echo '{"permissions": {"write": ["system.Everyone"]}}' | \
        http PUT http://localhost:8888/v1/buckets/a-bucket --auth user:pass


I am seeing an Exception error, what's wrong?
---------------------------------------------

Have a look at the :ref:`Troubleshooting section <troubleshooting>` to
see what to do.
