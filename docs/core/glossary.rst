Glossary
########

.. glossary::

    authentication policy
    authentication policies
        An authentication method enabled in :ref:`configuration <configuration-authentication>`

    Kinto-Core HTTP API
        A system of rules that explains the way to interact with the HTTP API
        :term:`endpoints` (utilities, synchronization, headers etc.), and how data
        is organized (JSON responses etc.).

    CRUD
        Acronym for Create, Read, Update, Delete

    endpoint
    endpoints
        An endpoint handles a particular HTTP verb at a particular URL.

    extensible
        «Extensible» means that the component behaviour can be overriden via
        lines of code. It differs from «:term:`pluggable`».

    Identity Provider
        An identity provider (abbreviated IdP) is a service in charge of managing
        identity information, and providing authentication endpoints (login forms,
        tokens manipulation etc.)

    HTTP API
        Multiple publicly exposed endpoints that accept HTTP requests and
        respond with the requested data, in the form of JSON.

    KISS
        «Keep it simple, stupid» is a design priciple which states that most
        systems work best if they are kept simple rather than made complicated.

    pluggable
        «Pluggable» means that the component can be replaced via configuration.
        It differs from «:term:`extensible`».

    resource
        A resource is a collection of records. A resource has two URLs, one for
        the collection and one for individual records.

    user id
    user identifier
    user identifiers
        A string that identifies a user. It is prefixed with the authentication
        policy name (eg. ``account:alice``, ``ldap:bob``, ``google:me@gmail.com``, ...).
        These identifiers are used to refer to users in :ref:`permissions <concepts-permissions>` or :ref:`groups <concepts-groups>`.

    object
    objects
        Also refered as «records», objects are stored by *Kinto-Core* resources.

    tombstone
    tombstones
        When a record is deleted in a resource, a tombstone is created to keep
        track of the deletion when polling for changes. A tombstone only contains
        the ``id`` and ``last_modified`` fields, everything else is really deleted.

    principal
    principals
        An entity that can be authenticated. Principals can be individual people,
        computers, services, or any group of such things.

    permission
    permissions
        An action that can be authorized or denied. read, write, create are
        permissions.

    Semantic Versioning
        A standard MAJOR.MINOR.PATCH versioning scheme.
        See http://semver.org/.

    ACE
    ACEs
    Access Control Entity
        An association of a principal, an object and a permission. For instance,
        (Alexis, article, write).

    ACL
    ACLs
    Access Control List
        A list of Access Control Entities (ACE).
