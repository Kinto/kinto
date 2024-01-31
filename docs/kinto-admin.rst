.. _kinto-admin:

Kinto Admin
###########

When the built-in plugin ``kinto.plugins.admin`` is enabled in
configuration, a Web admin UI is available at ``/v1/admin/``.

+-------------------------+----------+-------------------------------------------------+
| Setting name            | Default  | What does it do?                                |
+=========================+==========+=================================================+
| kinto.admin_assets_path | None     | Absolute path to the Admin UI assets files.     |
|                         |          | The folder must contain an ``index.html`` file. |
|                         |          | and a ``VERSION`` file.                         |
+-------------------------+----------+-------------------------------------------------+


* `See dedicated repo <https://github.com/Kinto/kinto-admin/>`_

.. image:: images/screenshot-kinto-admin-1.png
    :align: center

.. image:: images/screenshot-kinto-admin-2.png
    :align: center

.. image:: images/screenshot-kinto-admin-3.png
    :align: center

.. image:: images/screenshot-kinto-admin-4.png
    :align: center
