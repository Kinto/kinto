from zope.interface import implementer

from pyramid.interfaces import IAuthorizationPolicy

from pyramid.location import lineage

from pyramid.compat import is_nonstr_iter

from pyramid.security import (
    ACLAllowed,
    ACLDenied,
    Allow,
    Deny,
    Everyone,
    )

@implementer(IAuthorizationPolicy)
class ACLAuthorizationPolicy(object):
    """ An :term:`authorization policy` which consults an :term:`ACL`
    object attached to a :term:`context` to determine authorization
    information about a :term:`principal` or multiple principals.
    If the context is part of a :term:`lineage`, the context's parents
    are consulted for ACL information too.  The following is true
    about this security policy.

    - When checking whether the 'current' user is permitted (via the
      ``permits`` method), the security policy consults the
      ``context`` for an ACL first.  If no ACL exists on the context,
      or one does exist but the ACL does not explicitly allow or deny
      access for any of the effective principals, consult the
      context's parent ACL, and so on, until the lineage is exhausted
      or we determine that the policy permits or denies.

      During this processing, if any :data:`pyramid.security.Deny`
      ACE is found matching any principal in ``principals``, stop
      processing by returning an
      :class:`pyramid.security.ACLDenied` instance (equals
      ``False``) immediately.  If any
      :data:`pyramid.security.Allow` ACE is found matching any
      principal, stop processing by returning an
      :class:`pyramid.security.ACLAllowed` instance (equals
      ``True``) immediately.  If we exhaust the context's
      :term:`lineage`, and no ACE has explicitly permitted or denied
      access, return an instance of
      :class:`pyramid.security.ACLDenied` (equals ``False``).

    - When computing principals allowed by a permission via the
      :func:`pyramid.security.principals_allowed_by_permission`
      method, we compute the set of principals that are explicitly
      granted the ``permission`` in the provided ``context``.  We do
      this by walking 'up' the object graph *from the root* to the
      context.  During this walking process, if we find an explicit
      :data:`pyramid.security.Allow` ACE for a principal that
      matches the ``permission``, the principal is included in the
      allow list.  However, if later in the walking process that
      principal is mentioned in any :data:`pyramid.security.Deny`
      ACE for the permission, the principal is removed from the allow
      list.  If a :data:`pyramid.security.Deny` to the principal
      :data:`pyramid.security.Everyone` is encountered during the
      walking process that matches the ``permission``, the allow list
      is cleared for all principals encountered in previous ACLs.  The
      walking process ends after we've processed the any ACL directly
      attached to ``context``; a set of principals is returned.

    Objects of this class implement the
    :class:`pyramid.interfaces.IAuthorizationPolicy` interface.
    """

    def permits(self, context, principals, permission):
        """ Return an instance of
        :class:`pyramid.security.ACLAllowed` instance if the policy
        permits access, return an instance of
        :class:`pyramid.security.ACLDenied` if not."""

        acl = '<No ACL found on any object in resource lineage>'

        for location in lineage(context):
            try:
                acl = location.__acl__
            except AttributeError:
                continue

            if acl and callable(acl):
                acl = acl()

            for ace in acl:
                ace_action, ace_principal, ace_permissions = ace
                if ace_principal in principals:
                    if not is_nonstr_iter(ace_permissions):
                        ace_permissions = [ace_permissions]
                    if permission in ace_permissions:
                        if ace_action == Allow:
                            return ACLAllowed(ace, acl, permission,
                                              principals, location)
                        else:
                            return ACLDenied(ace, acl, permission,
                                             principals, location)

        # default deny (if no ACL in lineage at all, or if none of the
        # principals were mentioned in any ACE we found)
        return ACLDenied(
            '<default deny>',
            acl,
            permission,
            principals,
            context)

    def principals_allowed_by_permission(self, context, permission):
        """ Return the set of principals explicitly granted the
        permission named ``permission`` according to the ACL directly
        attached to the ``context`` as well as inherited ACLs based on
        the :term:`lineage`."""
        allowed = set()

        for location in reversed(list(lineage(context))):
            # NB: we're walking *up* the object graph from the root
            try:
                acl = location.__acl__
            except AttributeError:
                continue

            allowed_here = set()
            denied_here = set()

            if acl and callable(acl):
                acl = acl()

            for ace_action, ace_principal, ace_permissions in acl:
                if not is_nonstr_iter(ace_permissions):
                    ace_permissions = [ace_permissions]
                if (ace_action == Allow) and (permission in ace_permissions):
                    if ace_principal not in denied_here:
                        allowed_here.add(ace_principal)
                if (ace_action == Deny) and (permission in ace_permissions):
                        denied_here.add(ace_principal)
                        if ace_principal == Everyone:
                            # clear the entire allowed set, as we've hit a
                            # deny of Everyone ala (Deny, Everyone, ALL)
                            allowed = set()
                            break
                        elif ace_principal in allowed:
                            allowed.remove(ace_principal)

            allowed.update(allowed_here)

        return allowed
