Developer Guide
===============

Environment
-----------

Install the project dependencies with Poetry:

.. code-block:: bash

   poetry install

The development environment includes the Ansible CLI tools used by the
collection build and sanity sessions.

Collection Build
----------------

Build the local collection archive with:

.. code-block:: bash

   poetry run nox -s collection:build

The archive is written to ``.build_output/collections/``. The directory is
ignored by Git because the collection tarball is a generated release artifact,
not source.

Collection Sanity
-----------------

Run Ansible collection sanity checks with:

.. code-block:: bash

   poetry run nox -s collection:sanity

The session copies the checkout into a temporary
``ansible_collections/exasol/exasol`` layout before invoking
``ansible-test sanity``.

Toolbox Checks
--------------

Keep the Python toolbox checks green while developing collection code:

.. code-block:: bash

   poetry run nox -s format:check
   poetry run nox -s lint:code lint:typing lint:security
   poetry run nox -s test:unit test:integration
   poetry run nox -s docs:build

Real Exasol Integration Tests
-----------------------------

The pytest-driven integration tests can start a real Exasol backend through
``pytest-exasol-backend`` and execute Ansible playbooks through
``exasol-ansible-runner-wrapper``.

.. code-block:: bash

   poetry run -- nox -s test:integration -- --backend=onprem --itde-db-version 2025.1.8

Use ``--itde-db-version external`` together with the ``EXASOL_*`` environment
variables when an already running database should be used instead of a managed
ITDE container.
