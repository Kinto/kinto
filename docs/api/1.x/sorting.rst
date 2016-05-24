Sorting
#######

Plural endpoints support sorting of their contained elements. For
example, you can sort the records in a collection. To do this, provide
an additional query parameter specifying the sort key.

* ``/collection?_sort=-last_modified,field``

  Sorts according to ``last_modified`` descending, with ties being
  broken according to ``field`` ascending.

.. note::

    Ordering on a boolean field gives ``true`` values first.

.. note::

    Will return an error if a field is unknown.
