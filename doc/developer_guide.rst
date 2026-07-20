Developer Guide
===============

Environment
-----------

Install the project dependencies with Poetry:

.. code-block:: bash

   poetry install

The development environment includes the Ansible CLI tools used by the
collection build and sanity sessions.

Git Hooks
---------

Enable the project pre-commit and pre-push hooks after installing the Poetry
environment:

.. code-block:: bash

   poetry run -- pre-commit install --hook-type pre-commit --hook-type pre-push

The hooks run the configured local checks before commits and pushes. See the
Python toolbox Git hooks documentation for background and troubleshooting:
https://exasol.github.io/python-toolbox/main/user_guide/features/git_hooks/index.html

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

Test Types
----------

The collection uses several complementary test types. Choose the narrowest
test that proves the behavior you changed, and then add a broader test when the
boundary itself is part of the change.

* **Unit tests** in ``test/unit/`` exercise Python code in isolation, using
  fakes where a database or Ansible process would otherwise be needed. They
  cover SQL planning, input validation, result reporting, check mode, and
  error sanitization. Run them with ``poetry run nox -s test:unit``.
* **Acceptance-scenario contract tests** in
  ``test/unit/test_acceptance_scenario_contract.py`` keep the Gherkin feature
  files in ``specs/`` aligned with their pytest acceptance tests. They run as
  part of the unit-test suite; run only these checks with
  ``poetry run pytest test/unit/test_acceptance_scenario_contract.py``.
* **Collection integration tests** run through ``ansible-test integration``.
  They use the mocked ``pyexasol`` contract target and verify module
  interfaces, result shapes, argument handling, check mode behavior, and
  error sanitization without a running Exasol database. Run all of them with
  ``poetry run nox -s collection:integration``. To target one module, run
  ``poetry run -- nox -s collection:integration -- exasol_query``.
* **Runtime integration tests** in ``test/integration/ansible_modules/`` call
  the reusable Python runtime entry points directly against a real Exasol
  backend. They verify connection creation and database effects without the
  Ansible playbook layer. Follow :ref:`backend-test-environment` and run them
  with
  ``poetry run pytest test/integration/ansible_modules/ -q``.
* **Playbook acceptance tests** in ``test/integration/ansible_playbook/`` run
  documented feature scenarios through ``ansible-runner`` against a real
  Exasol backend. They verify the collection module, Ansible execution path,
  and resulting database state together. Follow
  :ref:`backend-test-environment` and run them with
  ``poetry run pytest test/integration/ansible_playbook/ -q``.
* **Installed-artifact E2E tests** build and install the Galaxy collection and
  the Python runtime package into isolated temporary locations before running
  smoke playbooks against a real Exasol backend. They protect the packaging
  boundary in addition to module behavior. Follow
  :ref:`backend-test-environment` and run them with
  ``poetry run pytest test/integration/test_installed_collection_e2e.py -q``.

Collection Integration Tests
----------------------------

.. code-block:: bash

   poetry run -- nox -s collection:integration -- exasol_query

Non-Mocked Exasol Integration Tests
-----------------------------------

.. _backend-test-environment:

Backend test environment
~~~~~~~~~~~~~~~~~~~~~~~~

Create an untracked ``.env`` file to hold the local backend-test configuration.
For an external disposable database, replace every placeholder with its
connection details:

.. code-block:: bash

   export PYTEST_ADDOPTS="--backend=onprem --itde-db-version=external --exasol-host=<host> --exasol-port=8563 --exasol-username=<user> --exasol-password=<password>"

``PYTEST_ADDOPTS`` selects the on-premises backend and tells
``pytest-exasol-backend`` to connect to the supplied instance rather than
starting an ITDE container. Do not put a shared,
development, or staging database in the `.env` file.

Load this configuration once in the shell that will run backend tests:

.. code-block:: bash

   source .env

All runtime integration, playbook acceptance, and installed-artifact E2E test
commands in this guide assume that setup.

Runtime integration, playbook acceptance, and installed-artifact E2E tests are
pytest-driven and can start an actual Exasol database backend through
``pytest-exasol-backend`` instead of using the mocked ``pyexasol`` module from
the collection integration tests. The playbook and E2E layers execute Ansible
through ``exasol-ansible-runner-wrapper``.

.. code-block:: bash

   poetry run -- nox -s test:integration -- --backend=onprem --itde-db-version 2026.1.0

To run a focused backend test, invoke pytest with a path or test selector:

.. code-block:: bash

   poetry run pytest test/integration/ansible_playbook/test_exasol_query.py -q

Use ``--itde-db-version external`` together with the connection options below
when an already running database should be used instead of a managed ITDE
container.

Before each DB-backed integration test, the shared pytest fixture drops all
non-system schemas, users, and roles from the target database. When using
``--itde-db-version external``, point the tests at a disposable custom database
instance only, not at a shared development or staging system.
