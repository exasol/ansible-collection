Developer Guide
===============

Environment
-----------

Install the project dependencies with Poetry:

.. code-block:: bash

   poetry install

The development environment includes the Ansible CLI tools used by the
collection build and sanity sessions.

Python Versions
---------------

The runtime package supports Python 3.12 through 3.14, as declared by
``requires-python = ">=3.12,<3.15"`` in ``pyproject.toml``.

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

Requirement Tracing
-------------------

Run OpenFastTrace locally with:

.. code-block:: bash

   poetry run nox -s requirements:trace

The session traces the whole repository from the project root so that
requirements, design, implementation, and tests can participate in one OFT
run.

Java 17 or newer and Maven must be available locally. On the first run, the
session downloads the OFT JAR into the local Maven repository, then executes ``trace .``.

Toolbox Checks
--------------

Keep the Python toolbox checks green while developing collection code:

.. code-block:: bash

   poetry run nox -s format:check
   poetry run nox -s lint:code lint:typing lint:security
   poetry run nox -s test:unit test:integration
   poetry run nox -s docs:build

Release Version Sync
--------------------

The derived release artifacts are synchronized automatically during
``release:prepare`` through the toolbox hook registered in ``noxconfig.py``:

.. code-block:: bash

   poetry run nox -- -s release:prepare -- --type patch

The hook updates ``galaxy.yml``, ``requirements.txt``, and
``meta/ee-requirements.txt`` to the version declared in ``pyproject.toml`` and
adds them to the release-prepare commit.

Collection Integration Tests
----------------------------

The standard Ansible integration target for ``exasol_query`` is a mocked
contract test. It runs through ``ansible-test integration`` and verifies the
module interface, result shape, argument handling, check mode behavior, and
error sanitization without requiring a running Exasol database.

.. code-block:: bash

   poetry run -- nox -s collection:integration -- exasol_query

Non-Mocked Exasol Integration Tests
-----------------------------------

The pytest-driven integration tests can start an actual Exasol database backend
through ``pytest-exasol-backend`` instead of using the mocked ``pyexasol`` module
from the Ansible collection target tests. They execute Ansible playbooks through
``exasol-ansible-runner-wrapper``.

.. code-block:: bash

   poetry run -- nox -s test:integration -- --backend=onprem --itde-db-version 2026.1.0

Use ``--itde-db-version external`` together with the ``EXASOL_*`` environment
variables when an already running database should be used instead of a managed
ITDE container.

Before each DB-backed integration test, the shared pytest fixture drops all
non-system schemas, users, and roles from the target database. When using
``--itde-db-version external``, point the tests at a disposable custom database
instance only, not at a shared development or staging system.
