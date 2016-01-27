.. _authenticating:

Authenticating to the Kinto API
###############################

First of all **Kinto doesn't handle users managements**.

You do not have such thing as user creation, user removal, user
password modifications, etc.

However Kinto handle users permissions, which means users are uniquely
identified in Kinto.


How is that possible?
---------------------

This is possible by plugging in Kinto with an Identity provider.

Multiple identity providers solutions are available such as OAuth,
SAML, x509, Hawk sessions, or Basic Tokens.

With regards to the application you are building you may want to plug
Github, Facebook, Google, or your company identity provider.

You may also want to use arbitrary tokens by making sure:

 - each user has a different one;
 - a user always uses the same token.

This is what we are doing within the the scope of this documentation.

We use the Basic Auth protocol like that: ``token:my-secret-token``


How can I generate a strong unique tokens?
------------------------------------------

I would recommand you to use more than 16 random bytes digested as
either a Base64 or a Hexadecimal string:

Here are two examples using Node and Python to generate 30 random bytes tokens:

.. code-block:: js

    var crypto = require("crypto");

	crypto.randomBytes(30).toString("hex"));
    // 8d11dfa2ab1fab42c841bcda834a66553624b03e8ef6bb5e8ec6fdd791a9

    crypto.randomBytes(30).toString("base64");
    // nkz6+hN9KVtXX6bZ9+RPof0NgF9hmm5gFhKpWbiM

.. code-block:: python

    import base64, os

    print(base64.b64encode(os.urandom(30)))
    # BxFNjp97FprmbdijOM78srl5DI+jjbYcLyRg5AVv

    print(os.urandom(30).encode('hex'))
    # 6573ba5016f740b04a0af7b59fe47045c0b9d4f94b1f613eaa11d276bc5e

Then you can use:

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/ \
        --auth "token:6573ba5016f740b04a0af7b59fe47045c0b9d4f94b1f613eaa11d276bc5e"

or:

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/ \
        --auth "token:nkz6+hN9KVtXX6bZ9+RPof0NgF9hmm5gFhKpWbiM"


How Kinto knows it is a valid Basic Auth token?
-----------------------------------------------

For each token, Kinto will calculate a unique user ID which is
related to your Kinto instance ``user_hmac_secret`` configuration.

.. note::

    Two Kinto instances using the same ``user_hmac_secret`` will
    generate the same user ID for a given Basic Auth token.

You can get the user ID generated for your token on the Kinto hello page:

.. code-block:: shell

    $ http https://kinto.dev.mozaws.net/v1/ --auth "token:my-secret"

.. code-block:: json

    HTTP/1.1 200 OK
    
    {
        "project_name": "kinto",
        "project_docs": "https://kinto.readthedocs.org/",
        "[...]": "[...]",
        "user": {
            "bucket": "...default-bucket-id...", 
            "id": "basicauth:c635be9375673027e9b2f357a3955a0a46b58aeface61930838b61e946008ab0"
        }
    }

As soon as this user ID is used to give permission on an object
(buckets, groups, collections, records), the user will be grant that
permission using the token.


How can I change the token for a given user?
--------------------------------------------

Asking yourself this question is a first sign that you should not be
using the Basic Auth authentication backend for your app.

Because the user ID is calculated from the token, changing the token,
will change the user ID.

You can generate other user IDs based on other tokens and give
permissions to them.

You can even create a group that could handle all the available tokens
for a given user, and change the token once for all without having to
change the permission of each object.

However you may prefer to use an identity provider who will handle the
user management part and always give you back the same user ID for the
same user (even if they use a different token to authenticated).

You can read our
:ref:`tutorial about how to plug the Github authorisation backend <tutorial-github>`.
