Exasol User Security Guide
==========================

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


Password Update Semantics
^^^^^^^^^^^^^^^^^^^^^^^^^^

The module operates under Exasol's limitation that existing passwords cannot be retrieved or compared.

As a result:

- ``update_password=on_create`` only sets the password during user creation.
- ``update_password=always`` always attempts a password update when the user exists.
- This will typically result in ``changed=true`` even if the password value is unchanged, as Exasol does not expose reversible password verification.

Security implications:

- Passwords are never retrieved from Exasol for comparison.
- This avoids exposing sensitive credential material via database introspection.
- Idempotency for password updates is intentionally limited due to database constraints.

Example verification scenario

.. code-block:: gherkin

    Scenario: Password is not exposed in failure output
        GIVEN login_password contains a secret value
        WHEN authentication fails
        THEN the error message must NOT contain the secret value
        AND the task output must redact the password
