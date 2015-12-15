##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

def inside(resource1, resource2):
    """Is ``resource1`` 'inside' ``resource2``?  Return ``True`` if so, else
    ``False``.

    ``resource1`` is 'inside' ``resource2`` if ``resource2`` is a
    :term:`lineage` ancestor of ``resource1``.  It is a lineage ancestor
    if its parent (or one of its parent's parents, etc.) is an
    ancestor.
    """
    while resource1 is not None:
        if resource1 is resource2:
            return True
        resource1 = resource1.__parent__

    return False

def lineage(resource):
    """
    Return a generator representing the :term:`lineage` of the
    :term:`resource` object implied by the ``resource`` argument.  The
    generator first returns ``resource`` unconditionally.  Then, if
    ``resource`` supplies a ``__parent__`` attribute, return the resource
    represented by ``resource.__parent__``.  If *that* resource has a
    ``__parent__`` attribute, return that resource's parent, and so on,
    until the resource being inspected either has no ``__parent__``
    attribute or which has a ``__parent__`` attribute of ``None``.
    For example, if the resource tree is::

      thing1 = Thing()
      thing2 = Thing()
      thing2.__parent__ = thing1

    Calling ``lineage(thing2)`` will return a generator.  When we turn
    it into a list, we will get::
    
      list(lineage(thing2))
      [ <Thing object at thing2>, <Thing object at thing1> ]
    """
    while resource is not None:
        yield resource
        # The common case is that the AttributeError exception below
        # is exceptional as long as the developer is a "good citizen"
        # who has a root object with a __parent__ of None.  Using an
        # exception here instead of a getattr with a default is an
        # important micro-optimization, because this function is
        # called in any non-trivial application over and over again to
        # generate URLs and paths.
        try:
            resource = resource.__parent__
        except AttributeError:
            resource = None

