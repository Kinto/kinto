.. _deployment:

Deployment good practices
#########################

*Kinto* is a python Web application that provides storage as a service.

It relies on 3 vital components:

* A Web stack;
* A database;
* An authentication service.

This document describes the strategy in order to deploy a full stack with the following properties:

* **Fail-safe**: respond in a way that causes a minimum of harm in case of failure;
* **Consistency**: all nodes see the same data at the same time;
* **Durability**: data of successful requests remains stored.

Even though it is related, this document does not cover the properties of the *Kinto* API (client race conditions etc.).


Python stack
============

High-availability
-----------------

* At least two nodes (e.g. Linux boxes)
* A load balancer, that spreads requests across the nodes (e.g. HAProxy)
* Each node runs several WSGI process workers (e.g. uWSGI)
* Each node runs a HTTP reverse proxy that spreads requests across the workers (e.g. Nginx)

Vertical scaling:

* Increase size of nodes
* Increase number of WSGI processes

Horizontal scaling:

* Increase number of nodes


Fail safe
---------

WSGI process crash:

* 503 error + ``Retry-After`` response header
* Sentry report
* uWSGI respawns a process (via Systemd for example)

Reverse proxy crash:

* The load balancer blacklists the node

If the load balancer or all nodes are down, the service is down.


Consistency
-----------

Every worker across every node are configured with the same database DSN.

See next section about details for database.


Configuration change
--------------------

Application:

* Modify configuration file
* Reload workers gracefully

Reverse proxy:

* Disable node in load balancer
* Restart reverse proxy
* Enable node in load balancer

Load balancer:

* See scheduled down time


Change application configuration
--------------------------------

* Modify configuration file
* Reload workers gracefully


Database
========

*Kinto* can be configured to persist data in several kinds of storage.

*PostgreSQL* is the one that we chose at Mozilla, mainly because:

* It is a mature and standard solution;
* It supports sorting and filtering of JSONB fields;
* It has an excellent reputation for data integrity.


High-availability
-----------------

Deploy a PostgreSQL cluster:

* a leader («*master*»);
* one or more replication followers («*slaves*»).
* A load balancer, that routes queries to take advantage of the cluster (pgPool)

Writes are sent to the master, and reads are sent to the master and slaves that
are up-to-date.

Vertical scaling:

* Increase size of nodes (RAM+#CPU)
* Increase shared_buffers and work_mem

Horizontal scaling:

* Increase number of nodes


Performance
-----------

* RAID
* Volatile data on SSD (indexes)
* Storage on HDD
* shared_buffers is like caching tables in memory
* work_mem is like caching joins (per connection)

Connection pooling:

* via load balancer
* via Kinto


Fail safe
---------

If the master fails, one slave can be promoted to be the new master.

Database crash:

* Restore database from last scheduled backup
* Restore WAL files since last backup


Consistency
-----------

* master streams WAL to slaves
* slaves are removed from load balance until their data is up-to-date with master


Durability
----------

* ACID
* WAL for transactions
* pgDump export :)


Pooling
-------

* automatic refresh of connections (TODO in Kinto)


Using Amazon RDS
----------------

* Consistency/Availability/Durability are handled by Postgresql RDS
* Use Elasticcache for Redis
* Use a EC2 Instance with uWSGI and Nginx deployed
* Use Route53 for loadbalancing


Authentication service
======================

Each request contains an ``Authorization`` header that needs to be verified by the authentication service.

In the case of Mozilla, *Kinto* is plugged with the *Firefox Accounts* OAuth service.


Fail safe
---------

With the *Firefox Accounts* policy, token verifications are cached for an amount of time.

.. code-block:: ini

    fxa-oauth.cache_ttl_seconds = 300  # 5 minutes

If the remote service is down, the cache will allow the authentication of known token for a while. However new tokens will generate a 401 or 503 error response.


Scheduled down time
===================

* Change Backoff setting in application configuration


About sharding
==============

`Sharding <https://en.wikipedia.org/wiki/Shard_%28database_architecture%29>`_ is
horizontal scaling, where the data is partitioned in different *shards*.

A client is automatically assigned a particular shard, depending for example:

* on the request authorization headers
* on the bucket or collection id

It is currently not possible to setup the sharding directly from the kinto
settings, however it is already possible to set it up manually. [#]_

.. [#] http://www.craigkerstiens.com/2012/11/30/sharding-your-database/


At the HTTP level
-----------------

It is possible to handle the sharding at the HTTP level. For instance, using
a third-party service that assigns a node to a particular user.

This has the advantage to be very flexible: new instances can be added and
this service is in charge of partitioning, downside being maintaining a new
service for it.

The `tokenserver <https://github.com/mozilla-services/tokenserver>`_ is a good
example of how sharding is done in Firefox Sync.

The first time they connect, clients are asking the token server for a node, and
then they talk directly with the node itself, without going through the token
server anymore, unless the node becomes unreachable.

At the load balancer level
--------------------------

The load balancer is the piece of software that takes all the requests upfront
and routes them to a different node, to make sure the load is equivalent on each
node.

It is possible to have the load balancer forcing the routing of a particular
request to a specific node.

It is basically the same idea as the previous one except that the server URL
always remains the same.

At the database level
----------------------

PostgreSQL and Redis have sharding support built-in.

The right database node is chosen based on some elements of the data query
(most probably bucket or collection id) and partionning is then performed
automatically.

As an example, see `pgPool <http://www.pgpool.net/mediawiki/index.php/Main_Page>`_
or :github:`pgShard <citusdata/pg_shard>` for ways to shard a PostgreSQL
database.
