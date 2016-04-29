.. _FAQ:

FAQ
===

How does Kinto compares to CouchDB / Remote Storage?
----------------------------------------------------

To see how Kinto compares to CouchDB & Remote Storage, read :ref:`the comparison table <comparison>`.

Can I encrypt my data?
----------------------

Kinto server stores any data you pass to it, whether it's encrypted or not. We believe
encryption should always be done on the client-side, and we make it `easy to use encryption in our Kinto.js client
<http://www.servicedenuages.fr/en/kinto-encryption-example>`_.


Is there a package for my Operating System?
-------------------------------------------

No, but it's a great idea. Maintaining packages for several platforms is time-consuming
and we're a small team.

Currently we make sure it's :ref:`easy to run with Docker or Python pip <get-started>`.

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


What is Cliquet? What is the difference between Cliquet and Kinto?
------------------------------------------------------------------

Cliquet is a toolkit for designing micro-services. Kinto is a server built
using that toolkit.

`Read more about the differences here
<http://www.servicedenuages.fr/en/why-cliquet>`_.


How does Kinto authenticate users ?
-----------------------------------

Kinto authentication system is pluggable and controlled from settings.

By default it ships with a very simple (but limited) *Basic Authentication* policy, which
distinguishes users using the value provided in the header.

See also:

* :ref:`How to implement a custom authentication <tutorial-github>`
* :ref:`Kinto API documentation about authentication <authentication>`

.. note::

    We'd be delighted to add more built-in authentication methods into Kinto.
    Please reach out if you're interested!


I am seeing an Exception error, what's wrong?
---------------------------------------------

Have a look at the :ref:`Troubleshooting section <troubleshooting>` to
see what to do.
