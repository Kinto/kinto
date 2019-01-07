.. _administrative-endpoints:

Administrative endpoints
########################

Some endpoints are not directly useful for users, but can be part of
the implementation of a complete system.

These endpoints are generally not designed to be used directly by
users, but only be certain "operator" users. By default the permission
to use them is granted to no one (i.e. the endpoints are disabled). To
use them, you will have to update your config to include some
principals who are granted permission to use them. For example, if
your user ID is ``account:admin`` and you want to enable the "deleting
user data" endpoint for your user, you would add to your
``kinto.ini``::

    kinto.user-data_delete_principals = account:admin

.. _user-data-delete:

Deleting user data
==================

.. http:delete:: /__user_data__/(principal)

   :synopsis: Deletes all data for a given user.

   Permission: ``user-data_delete_principals``

   **Example Request**

   .. sourcecode:: bash

      $ http DELETE 'localhost:8888/v1/__user_data__/basicauth:367cfeb65b3ef39459656b562a11e306874e5b4bdc48d14a2ce9ba1f65015a0f' -a 'bob:p4ssw0rd'
      {
        "data": {
          "principal": "basicauth:367cfeb65b3ef39459656b562a11e306874e5b4bdc48d14a2ce9ba1f65015a0f"
        }
      }

   Deletes data belonging to a user. Data "belonging" to a user is
   defined as any data that can only be written to by that
   user. Deletion of this data cascades as normal, i.e. deleting a
   user's bucket deletes all data in that bucket, whether "belonging"
   to that user or not. Additionally:

   - Remove this user's permission from all objects.
   - Remove the user from all groups they are in.
   - If the user is a group, remove the group from all users.

   The motivation for this endpoint comes from trying to achieve GDPR compliance.
