.. _tutorial-id-generator:

How to define and use a custom ID generator?
============================================

By default, Kinto uses UUID4 as ``id`` for its records. In some cases, it might
not be what you want. But you're not out of luck, there is a way to configure
Kinto to use a different ``id_generator`` than the default one.

Let's define a "name generator", which will output 8 random characters
(uppercase or lowercase).

.. code-block:: python

    import random
    import string

    from cliquet.storage import generators


    class NameGenerator(generators.Generator):

        regexp = r'^[a-zA-Z0-9-_]{8}$'

        def __call__(self):
            ascii_letters = ('abcdefghijklmopqrstuvwxyz'
                             'ABCDEFGHIJKLMOPQRSTUVWXYZ')
            alphabet = ascii_letters + string.digits + '-_'
            letters = [random.choice(ascii_letters + string.digits)]
            letters += [random.choice(alphabet) for x in range(7)]
            return ''.join(letters)


Note that you actually need to define both the generator **and** the validator,
which can be provided as a regexp.

Okay, once we've got this new generator, we can put it in a file named
``name_generator.py``, and then configure the kinto server to use this
generator to actually generate the record IDs.

In your `kinto.ini` configuration file, set the ``kinto.id_generator``
setting:

.. code-block:: ini

    kinto.id_generator = name_generator.NameGenerator

And then run your server as usual

.. code-block:: bash

    $ pserve config/kinto.ini

Now, if you try to generate a new record, you should have the new ID used,
well done!

.. code-block:: bash

    $ echo '{"data": {"yeah": "oh"}}' | http POST http://localhost:8888/v1/buckets/default/collections/tasks/records --auth user:pass

.. code-block:: http
    :emphasize-lines: 10

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
    Content-Length: 171
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 25 Feb 2016 22:13:20 GMT
    Server: waitress

    {
        "data": {
            "id": "fm64GtdA",
            "last_modified": 1456438400719,
            "yeah": "oh"
        },
        "permissions": {
            "write": [
                "basicauth:2025f72e6967625e3e878288b55d8946839e51968d11991b8a7dd0f040d4b6f0"
            ]
        }
    }
