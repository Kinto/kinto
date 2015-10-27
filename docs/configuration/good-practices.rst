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

Even though it is related, this document does not cover the properties of the *Kinto* protocol (client race conditions etc.).


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


Sharding
--------

* Use buckets+collections or userid to shard ?

Via pgPool:

* Flexible
* Tedious to configure

Via Kinto code:

* not implemented yet
* battery-included (via INI configuration)


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
