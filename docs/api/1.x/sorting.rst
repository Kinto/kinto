Sorting
#######

When requesting elements (such as records) from a plural endpoint
(such as a collection), the results can be sorted using an additional
query parameter.

* ``/collection?_sort=-last_modified,field``

  Sorts according to ``last_modified`` descending, with ties being
  broken according to ``field`` ascending.

.. note::

    Ordering on a boolean field gives ``true`` values first.

.. note::

    Will return an error if a field is unknown.
