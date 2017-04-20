.. _sorting:

Sorting
#######

Plural endpoints support sorting of their contained elements. For
example, you can sort the records in a collection. To do this, provide
an additional query parameter specifying the sort key.

* ``/collection?_sort=field,-last_modified``

Sorts according to ``field`` ascending, with ties being
broken according to ``last_modified`` descending.

.. note::

    * Sort order is ``-last_modified`` by default
    * Sorting by sub-object is possible (e.g. ``?_sort=field.subfield``)
    * Ordering on a boolean field gives ``true`` values first.
