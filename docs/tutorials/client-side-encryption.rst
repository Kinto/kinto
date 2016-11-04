Client-side encryption
======================

If you want to encrypt data that is uploaded to the cloud by an offline-first app, it makes sense to keep the local copy of the data in-the-clear, and encrypt the data only just before it is uploaded.

With Kinto, your records can have a text field that stores the encrypted attributes:

.. code-block:: json

    {
        "id": "498e1015-92a5-46d5-9008-2b157338bbd1",
        "last_modified": 1478257378677,
        "payload": "b0WucBajkcjNRKOipTWDetHjn7VTQnxqjVz/DW5cyVtinBpq0+oC2H/W6Di3K0pEAzKmmxJBFKDb4LmWIN2OSj9z4HJMmHLQ8qDXWoZ//aOeJWlDlsTDBcBgJzNqX1Mz/frYMo1iLD5ULsW4iXexZbyI7WWAqZPy4l0twyViSMXAH7Memy4HPDf0R4s6vn3g"
    }

The client will encrypt the payload before sending to the server, and decrypt it upon reception.

See the `online demo <https://michielbdejong.github.io/kinto-encryption-example/>`_ that leverages
kinto.js and WebCrypto, and read `the complete tutorial <http://www.servicedenuages.fr/en/kinto-encryption-example>`_!
