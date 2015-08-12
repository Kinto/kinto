.. figure :: images/logo.svg
    :align: center

    **Kinto** — Store, Sync, Share and Self-Host.

Kinto is a lightweight JSON storage service, with synchronisation and sharing
abilities.

Introduction
============

Get a high level overview of what Kinto is.

.. raw:: html

    <table class="contentstable" align="center" style="margin-left: 30px">
    <tr>
        <td width="50%" class="">
            <h3><a href="{{ pathto("tutorial") }}">Rationale</a></h3>
            <p>Get a high level overview of what Kinto is.</p>
            <p><a class="reference external" href="test">High level overview</a> | <a class="reference external" href="test">Frequently Asked Questions</a> | <a class="reference external" href="test">Use cases</a> | <a class="reference external" href="test">How does Kinto compare with X</a></p>
        </td>
        <td width="50%">
            <h3><a href="{{ pathto("tutorial") }}">Tutorial</a></h3>
            <p>The easiest way to get started with Kinto.</p>
            <p><a class="reference external" href="test">Store your data</a> | <a class="reference external" href="test">Sync among devices</a> | <a class="reference external" href="test">Share between users</a></p>
        </td>
    </tr>
    <tr>
        <td width="50%">
            <h3><a href="{{ pathto("tutorial") }}">Concepts, terms and design</a></h3>
            <p>Learn the concepts you need to interact with a Kinto server.</p>
            <a class="reference external" href="test">Overview</a> | <a class="reference external" href="test">Buckets</a> | <a class="reference external" href="test">Collections</a> | <a class="reference external" href="test">Records</a> | <a class="reference external" href="test">Groups</a> | <a class="reference external" href="test">Permissions inheritance</a>
        </td>
        <td width="50%">
            <h3><a href="{{ pathto("tutorial") }}">APIs</a></h3>
            <p>Extensive HTTP endpoints documentation.</p>
            <a class="reference external" href="test">Endpoints</a> | <a class="reference external" href="test">Authentication</a> | <a class="reference external" href="test">Pagination</a> | <a class="reference external" href="test">Synchronisation</a> | <a class="reference external" href="test">How to handle permissions</a>
        </td>
    </tr>
    <tr>
        <td width="50%">
            <h3><a href="{{ pathto("tutorial") }}">Configuration and Deployment</a></h3>
            <p>Discover how to install configure and self-host your Kinto server.</p>
            <a class="reference external" href="test">Installation</a> | <a class="reference external" href="test">Configuration</a> | <a class="reference external" href="test">Production setup</a> | <a class="reference external" href="test">Architecture</a>
        </td>
        <td width="50%">
            <h3><a href="{{ pathto("tutorial") }}">Community</a></h3>
            <p>Find help here about contributing, troubleshooting and communication channels.</p>
            <a class="reference external" href="test">How to contribute</a> | <a class="reference external" href="test">Communication channels</a> | <a class="reference external" href="test">Getting support</a> | <a class="reference external" href="test">Troubleshooting</a>
        </td>
    </tr>
    </table>


Getting started
===============

.. code-block:: bash

    $ pip install kinto
    $ wget https://raw.githubusercontent.com/Kinto/kinto/master/config/kinto.ini
    $ pserve kinto.ini


Tutorial
========

Sometimes it is easier to get started by following a
tutorial. :ref:`Learn how to store, manage and sync your data <tutorial>`.

Using the HTTP API
==================

Interaction with a *Kinto* instance happens at some point using HTTP calls.
Find all you need to know via the links below:

- Buckets: :ref:`Working with buckets <buckets>`
- Collections : :ref:`Handling collections <collections>` |
  :ref:`Sending and retrieving records <records>`
- Permissions: :ref:`Understanding permissions <permissions>` |
  :ref:`Handling groups <groups>`

Deployment
==========

- From scratch: :ref:`installation`.
- Deployment: :ref:`Good practices <deployment>` | :ref:`configuration`

Community
=========

- How to contribute: :ref:`Guidelines <contributing>`

Table of content
================

.. toctree::
   :maxdepth: 1

   installation
   tutorial
   configuration
   deployment
   permissions
   api/index
   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
