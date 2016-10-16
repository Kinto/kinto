def Preparer(value):
    """
    A preparer is called after deserialization of a value but before
    that value is validated.

    Any modifications to ``value`` required should be made by
    returning the modified value rather than modifying in-place.

    If no modification is required, then ``value`` should be returned
    as-is.
    """


def Validator(node, value):
    """
    A validator is called after preparation of the deserialized value.

    If ``value`` is not valid, raise a :class:`colander.Invalid`
    instance as an exception after.

    ``node`` is a :class:`colander.SchemaNode` instance, for use when
    raising a :class:`colander.Invalid` exception.
    """

class Type(object):
    def serialize(self, node, appstruct):
        """
        Serialize the :term:`appstruct` represented by ``appstruct``
        to a :term:`cstruct`.  The serialization should be composed of
        one or more objects which can be deserialized by the
        :meth:`colander.interfaces.Type.deserialize` method of this
        type.

        ``node`` is a :class:`colander.SchemaNode` instance.

        ``appstruct`` is an :term:`appstruct`.

        If ``appstruct`` is the special value :attr:`colander.null`,
        the type should serialize a null value.

        If the object cannot be serialized for any reason, a
        :exc:`colander.Invalid` exception should be raised.
        """

    def deserialize(self, node, cstruct):
        """
        Deserialze the :term:`cstruct` represented by ``cstruct`` to
        an :term:`appstruct`.  The deserialization should be composed
        of one or more objects which can be serialized by the
        :meth:`colander.interfaces.Type.serialize` method of this
        type.

        ``node`` is a :class:`colander.SchemaNode` instance.

        ``cstruct`` is a :term:`cstruct`.

        If the object cannot be deserialized for any reason, a
        :exc:`colander.Invalid` exception should be raised.
        """

