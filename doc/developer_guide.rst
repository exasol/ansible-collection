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

The runtime package supports Python 3.11 through 3.13, as declared by
``requires-python = ">=3.11,<3.14"`` in ``pyproject.toml``. Python 3.14 is not
supported yet because it is outside the tested project matrix and the Ansible
and toolbox dependency stack has not been validated with it. When adding support
for a new Python minor version, update ``pyproject.toml``, ``noxconfig.py``, and
the CI matrices together.

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

   poetry run -- nox -s test:integration -- --backend=onprem --itde-db-version 2025.1.8

Use ``--itde-db-version external`` together with the ``EXASOL_*`` environment
variables when an already running database should be used instead of a managed
ITDE container.

Security Considerations
-----------------------

Principle of Least Privilege
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The collection does not bypass Exasol's authorization model. All operations execute using the permissions of the authenticated Exasol account.

Module ``exasol_user`` requires the connected account to already possess the corresponding administrative privileges.

The collection does not implement privilege elevation.

Benefits:

- Existing Exasol authorization rules remain authoritative.
- Administrative boundaries are enforced by the database.
- Playbooks cannot grant permissions unavailable to the authenticated account.

Secret Handling
^^^^^^^^^^^^^^^

Credentials and passwords are treated as sensitive values.

Controls:

- ``login_password`` is marked with ``no_log=True``.
- User passwords are marked with ``no_log=True``.
- Authentication failures must not expose credentials.
- Error messages are sanitized before being returned to Ansible.
- Documentation recommends storing secrets in Ansible Vault.

Example verification scenario:

.. code-block:: gherkin

   Scenario: Password is not exposed in failure output
     GIVEN login_password contains a secret value
     WHEN authentication fails
     THEN the error message MUST NOT contain the secret value
     AND the task output MUST redact the password