User Guide
==========

Installation
------------

Install the collection from Ansible Galaxy:

.. code-block:: bash

   ansible-galaxy collection install exasol.exasol

Collection modules also require the Python runtime package
``exasol-ansible-modules``. Install it separately in the Python environment
that executes the modules:

.. code-block:: bash

   python -m pip install exasol-ansible-modules

For a pinned setup, use the version that matches the installed collection.

Recommended Execution Environment
---------------------------------

We recommend using ``ansible-builder`` to create an execution environment and
``ansible-navigator`` to run playbooks with that environment. Follow the
:doc:`execution-environment getting-started guide <getting_started>` for a
complete project layout, image definition, inventory, and read-only playbook.

If you do not use an execution environment, install
``exasol-ansible-modules`` for the configured ``ansible_python_interpreter`` on
the control node or remote host that executes the module.

Security And Secret Handling
----------------------------

Vault-Backed Secrets
^^^^^^^^^^^^^^^^^^^^
`uman~document-vault-backed-secret-handling~1`

Store Exasol credentials and other secret values in Ansible Vault or an
equivalent external secret manager. Pass secrets into module parameters such as
``login_password`` from that protected source instead of writing them directly
in playbooks, inventory, CI variables that are printed in logs, or reusable
examples.

Use the same pattern for every automation environment that runs the collection:
the playbook should receive the current secret value at runtime, and logs or
shared artifacts should contain only variable names or redacted module output.

``exasol_query`` is an explicit exception for SQL text: its
``executed_queries`` result returns the SQL supplied to the module. Never embed
passwords, tokens, or other secrets in ``query`` text. Use ``positional_args``
or ``named_args`` for values that must be bound to a single statement, and
source those values from Vault or another protected secret manager.


.. raw:: html

   <!--

Status: draft
Covers:
- dsn~document-vault-backed-secret-handling~1

.. raw:: html

   -->

Secret Rotation And Revocation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
`uman~keep-secret-rotation-and-revocation-outside-the-collection~1`

Rotate and revoke credentials in their source systems: update the external
secret store and the corresponding Exasol account state, then run playbooks
with the updated secret values. The collection does not retain credentials
across tasks and does not provide a credential-rotation workflow of its own.

When a credential is revoked or replaced, remove or update the old value in the
secret source used by Ansible. Subsequent collection tasks should receive the
new value through normal playbook variable resolution.


.. raw:: html

   <!--

Status: draft
Covers:
- dsn~keep-secret-rotation-and-revocation-outside-the-collection~1

.. raw:: html

   -->

Least-Privilege Service Accounts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
`uman~require-least-privilege-service-accounts-for-automation-tiers~1`

Use separate Exasol service accounts for separate automation roles, and grant
each account only the privileges needed by the playbooks it runs. For example,
an account used for metadata checks does not need the same privileges as an
account that manages users, roles, schemas, grants, or trusted direct SQL
through ``exasol_query``.

Keep these privilege boundaries in Exasol account provisioning and in the
secret store that supplies the credentials. The collection executes with the
permissions of the authenticated account and cannot downgrade an account that
has already been granted broader privileges than the playbook requires.

Status: draft

.. raw:: html

   <!--

Covers:
- dsn~require-least-privilege-service-accounts-for-automation-tiers~1

.. raw:: html

   -->

Basic Playbook
--------------

Module Names And FQCNs
^^^^^^^^^^^^^^^^^^^^^^
`uman~explain-fqcn-module-naming~1`

Ansible examples in this guide usually use fully qualified collection names
(FQCNs), such as ``exasol.exasol.exasol_query``. The three parts are:

* ``exasol``: the Ansible Galaxy namespace
* ``exasol``: the collection name
* ``exasol_query``: the module name

The apparent repetition in names such as ``exasol.exasol.exasol_query`` is
therefore expected Ansible convention. It appears because the namespace,
collection, and module names all share the Exasol project prefix.

Use FQCNs in reusable playbooks, shared snippets, role tasks, and documentation
examples because they are unambiguous without relying on surrounding playbook
context. Short module names are also valid when the playbook declares the
collection:

.. code-block:: yaml

   ---
   - hosts: localhost
     gather_facts: false
     collections:
       - exasol.exasol
     tasks:
       - name: Read Exasol version metadata
         exasol_query:
           login_host: db.example.com
           login_user: "{{ vault_exasol_user }}"
           login_password: "{{ vault_exasol_password }}"
           query: SELECT PARAM_VALUE FROM EXA_METADATA

.. raw:: html

   <!--

Status: draft

Covers:
- scn~fully-qualified-collection-names-are-explained~1

.. raw:: html

   -->

Declare the collection in a playbook and call modules with Exasol connection
parameters:

.. code-block:: yaml

   ---
   - hosts: localhost
     gather_facts: false
     collections:
       - exasol.exasol
     tasks:
       - name: Read Exasol version metadata
         exasol.exasol.exasol_query:
           login_host: db.example.com
           login_user: "{{ vault_exasol_user }}"
           login_password: "{{ vault_exasol_password }}"
           query: >-
             SELECT PARAM_VALUE
             FROM EXA_METADATA
             WHERE PARAM_NAME = 'databaseProductVersion'

exasol_query
------------
`uman~document-direct-sql-secret-exposure~1`

.. raw:: html

   <!--

Status: draft

Covers:
- scn~direct-sql-guidance-protects-secrets~1

.. raw:: html

   -->

Use ``exasol.exasol.exasol_query`` to execute SQL statements directly from an
Ansible playbook. ``query`` can be a single SQL string or a list of SQL
statements. A list runs on one Exasol connection in the supplied order.

Read-only statements report ``changed=false``. DDL and DML statements report
``changed=true``. The result contains rows from the last statement in
``query_result``, one result list per statement in ``query_all_results``, and
per-statement ``rowcount`` and ``execution_time_ms`` values.

Bound arguments are available for single-statement queries only. Use
``positional_args`` for ``?`` placeholders and ``named_args`` for ``:name``
placeholders. Statement batches do not accept bound arguments; split the batch
into separate tasks if each statement needs its own bindings.

Validation Behavior
^^^^^^^^^^^^^^^^^^^

``exasol_query`` fails validation for argument-binding cases that would be
ambiguous or unsafe to execute:

* ``positional_args`` or ``named_args`` with a statement batch. The module does
  not infer which arguments belong to which statement.
* A different number of ``?`` placeholders and ``positional_args`` values.
* Missing ``named_args`` values for ``:name`` placeholders, or extra
  ``named_args`` entries that are not used by the statement.

For statement batches that need bindings, split the batch into separate
``exasol_query`` tasks so each task has one SQL statement and one explicit
argument set.

.. code-block:: yaml

   - name: Bind positional and named values in a single statement
     exasol.exasol.exasol_query:
       login_host: db.example.com
       login_user: "{{ vault_exasol_user }}"
       login_password: "{{ vault_exasol_password }}"
       query: SELECT ? AS A, :name AS B
       positional_args:
         - 42
       named_args:
         name: example

Run statement batches without bound arguments:

.. code-block:: yaml

   - name: Run a batch on one Exasol connection without bound arguments
     exasol.exasol.exasol_query:
       login_host: db.example.com
       login_user: "{{ vault_exasol_user }}"
       login_password: "{{ vault_exasol_password }}"
       query:
         - CREATE SCHEMA IF NOT EXISTS demo
         - CREATE OR REPLACE TABLE demo.t (id DECIMAL(18,0))
         - INSERT INTO demo.t VALUES (1)
         - SELECT COUNT(*) AS row_count FROM demo.t

In check mode, read-only statements are executed. If any statement in a batch
is writable, the whole batch is skipped and the module reports the predicted
change. This avoids partially executing a mixed read/write batch.

Because ``executed_queries`` returns the supplied SQL, do not put secret values
in query text. Use the bound arguments described above for a single statement.

.. code-block:: yaml

   - name: Preview a mixed read-write batch in check mode
     exasol.exasol.exasol_query:
       login_host: db.example.com
       login_user: "{{ vault_exasol_user }}"
       login_password: "{{ vault_exasol_password }}"
       query:
         - SELECT COUNT(*) AS SCHEMA_COUNT FROM EXA_SCHEMAS
         - CREATE SCHEMA demo_check_mode
     check_mode: true

exasol_script
-------------

Use ``exasol.exasol.exasol_script`` to execute a multi-statement SQL script
directly from an Ansible playbook. Unlike ``exasol_query``, ``script`` is
always a single string, and the module relies on pyexasol's
``execute_sql_script`` capability to split it into statements. Semicolons
inside string literals, quoted identifiers, comments, and Exasol script
bodies do not terminate statements; a script body such as a ``CREATE ...
SCRIPT`` definition is terminated by a standalone ``/`` line instead.

.. code-block:: yaml

   - name: Run a batch of statements as one script
     exasol.exasol.exasol_script:
       login_host: db.example.com
       login_user: "{{ vault_exasol_user }}"
       login_password: "{{ vault_exasol_password }}"
       script: |
         CREATE SCHEMA IF NOT EXISTS demo;
         CREATE OR REPLACE TABLE demo.t (id DECIMAL(18,0));
         INSERT INTO demo.t VALUES (1);

   - name: Create a script whose body contains semicolons
     exasol.exasol.exasol_script:
       login_host: db.example.com
       login_user: "{{ vault_exasol_user }}"
       login_password: "{{ vault_exasol_password }}"
       script: |
         CREATE SCRIPT demo.double_value(x) AS
         function run(ctx)
             local x = ctx.x; return x * 2
         end
         /

If a statement fails, pyexasol raises the original error and later statements
do not run. ``exasol_script`` does not accept ``positional_args`` or
``named_args``; pyexasol does not support bound parameters for scripts.

Check mode classifies the whole script as read-only or not, the same way
``exasol_query`` classifies a multi-statement batch. A script made up only of
read-only statements executes normally and reports ``changed=false``. Any
other script is skipped, and the module reports ``changed=true`` with the
whole supplied script as a single predicted entry in ``executed_queries``,
rather than the real per-statement breakdown that execution produces.

.. code-block:: yaml

   - name: Preview a script that would create a schema
     exasol.exasol.exasol_script:
       login_host: db.example.com
       login_user: "{{ vault_exasol_user }}"
       login_password: "{{ vault_exasol_password }}"
       script: |
         CREATE SCHEMA demo_check_mode;
     check_mode: true

exasol_info
-----------
`uman~document-public-module-workflows~1`

.. raw:: html

   <!--

Status: draft

Covers:
- scn~public-module-workflows-are-documented~1

.. raw:: html

   -->

Use ``exasol.exasol.exasol_info`` to gather basic Exasol server information
from read-only metadata queries. The module returns the Exasol version,
database name, and cluster size, and it always reports ``changed=false``.

The module uses the same connection parameters as the other collection
modules. Provide the Exasol login settings in the task as shown below:

.. code-block:: yaml

   ---
   - hosts: localhost
     gather_facts: false
     collections:
       - exasol.exasol
     tasks:
       - name: Gather Exasol server information
         exasol.exasol.exasol_info:
           login_host: db.example.com
           login_user: "{{ vault_exasol_user }}"
           login_password: "{{ vault_exasol_password }}"

Use check mode if you want to verify the module behavior in a dry run. The
module still queries metadata and returns the same information:

.. code-block:: yaml

   - name: Gather Exasol server information in check mode
     exasol.exasol.exasol_info:
       login_host: db.example.com
       login_user: "{{ vault_exasol_user }}"
       login_password: "{{ vault_exasol_password }}"
     check_mode: true

exasol_grants
--------------

Use ``exasol.exasol.exasol_grants`` to grant or revoke requested Exasol
privileges for exactly one user or role. The module checks Exasol privilege
metadata first, so repeated runs report ``changed=false`` when the requested
grant state already matches the database.

``state=present`` grants missing privileges. ``state=absent`` revokes only the
privileges listed in the task; it does not remove unrelated grants from the
principal.

Supported principals and grants:

* exactly one principal, either ``user`` or ``role``
* direct system privileges through ``system_privileges``
* schema-level object privileges through ``object_privileges`` with ``schema``
  and no ``object``
* schema-qualified object privileges through ``object_privileges`` with both
  ``schema`` and ``object``

Supply at least one requested privilege. When an optional privilege list is not
needed, omit the option instead of passing an empty list.

Supported system privileges:

``ACCESS ANY CONNECTION``, ``ALTER ANY CONNECTION``, ``ALTER ANY SCHEMA``,
``ALTER ANY TABLE``, ``ALTER ANY VIRTUAL SCHEMA``,
``ALTER ANY VIRTUAL SCHEMA REFRESH``, ``ALTER SYSTEM``, ``ALTER USER``,
``CREATE ANY FUNCTION``, ``CREATE ANY SCRIPT``, ``CREATE ANY TABLE``,
``CREATE ANY VIEW``, ``CREATE CONNECTION``, ``CREATE FUNCTION``,
``CREATE ROLE``, ``CREATE SCHEMA``, ``CREATE SCRIPT``, ``CREATE SESSION``,
``CREATE TABLE``, ``CREATE USER``, ``CREATE VIEW``,
``CREATE VIRTUAL SCHEMA``, ``DELETE ANY TABLE``, ``DROP ANY CONNECTION``,
``DROP ANY FUNCTION``, ``DROP ANY ROLE``, ``DROP ANY SCHEMA``,
``DROP ANY SCRIPT``, ``DROP ANY TABLE``, ``DROP ANY VIEW``,
``DROP ANY VIRTUAL SCHEMA``, ``DROP USER``, ``EXECUTE ANY FUNCTION``,
``EXECUTE ANY SCRIPT``, ``EXPORT``, ``GRANT ANY CONNECTION``,
``GRANT ANY OBJECT PRIVILEGE``, ``GRANT ANY PRIVILEGE``, ``GRANT ANY ROLE``,
``IMPERSONATE ANY USER``, ``IMPORT``, ``INSERT ANY TABLE``,
``KILL ANY SESSION``, ``MANAGE CONSUMER GROUPS``,
``SELECT ANY DICTIONARY``, ``SELECT ANY TABLE``, ``SET ANY CONSUMER GROUP``,
``UPDATE ANY TABLE``, ``USE ANY CONNECTION``, and ``USE ANY SCHEMA``.

Supported object privileges:

``ACCESS``, ``ALTER``, ``DELETE``, ``EXECUTE``, ``IMPERSONATION``, ``INSERT``,
``REFERENCES``, ``REFRESH``, ``SELECT``, ``UPDATE``, and ``USAGE``.

Supported object types are ``function``, ``script``, ``table``, ``view``, and
``virtual_schema``. The ``object_type`` option is optional; omit it for
schema-level grants and ordinary table grants.

This version does not manage role grants, connection object grants,
``WITH ADMIN OPTION``, ``WITH GRANT OPTION``, exclusive reconciliation, or broad
``ALL PRIVILEGES`` requests. User and role names are exact Exasol identifier
values. Schema and object names use the collection's conservative
regular-identifier validation.

Grant a system privilege to a user:

.. code-block:: yaml

   - name: Grant CREATE SESSION to an application user
     exasol.exasol.exasol_grants:
       login_host: db.example.com
       login_user: "{{ vault_exasol_admin_user }}"
       login_password: "{{ vault_exasol_admin_password }}"
       user: app_user
       system_privileges:
         - CREATE SESSION

Grant multiple system privileges to a user:

.. code-block:: yaml

   - name: Grant application user login and schema creation privileges
     exasol.exasol.exasol_grants:
       login_host: db.example.com
       login_user: "{{ vault_exasol_admin_user }}"
       login_password: "{{ vault_exasol_admin_password }}"
       user: app_user
       system_privileges:
         - CREATE SESSION
         - CREATE SCHEMA
         - USE ANY SCHEMA

Grant a schema-scoped object privilege to a role:

.. code-block:: yaml

   - name: Grant schema usage to a reader role
     exasol.exasol.exasol_grants:
       login_host: db.example.com
       login_user: "{{ vault_exasol_admin_user }}"
       login_password: "{{ vault_exasol_admin_password }}"
       role: app_reader
       object_privileges:
         - schema: app_schema
           privileges:
             - USAGE

Grant multiple object privileges to a role:

.. code-block:: yaml

   - name: Grant reader and writer privileges on application objects
     exasol.exasol.exasol_grants:
       login_host: db.example.com
       login_user: "{{ vault_exasol_admin_user }}"
       login_password: "{{ vault_exasol_admin_password }}"
       role: app_writer
       object_privileges:
         - schema: app_schema
           privileges:
             - USAGE
         - schema: app_schema
           object: fact_sales
           privileges:
             - SELECT
             - INSERT
             - UPDATE
         - schema: app_schema
           object: sales_view
           object_type: view
           privileges:
             - SELECT

Grant system and object privileges in one task:

.. code-block:: yaml

   - name: Grant all requested privileges for an application service user
     exasol.exasol.exasol_grants:
       login_host: db.example.com
       login_user: "{{ vault_exasol_admin_user }}"
       login_password: "{{ vault_exasol_admin_password }}"
       user: app_service
       system_privileges:
         - CREATE SESSION
       object_privileges:
         - schema: app_schema
           privileges:
             - USAGE
         - schema: app_schema
           object: fact_sales
           privileges:
             - SELECT
             - INSERT

Revoke a requested object privilege without touching other grants:

.. code-block:: yaml

   - name: Revoke table SELECT from a user
     exasol.exasol.exasol_grants:
       login_host: db.example.com
       login_user: "{{ vault_exasol_admin_user }}"
       login_password: "{{ vault_exasol_admin_password }}"
       user: app_user
       state: absent
       object_privileges:
         - schema: app_schema
           object: fact_sales
           privileges:
             - SELECT

Revoke multiple requested privileges from a role:

.. code-block:: yaml

   - name: Revoke write privileges while keeping unrelated grants intact
     exasol.exasol.exasol_grants:
       login_host: db.example.com
       login_user: "{{ vault_exasol_admin_user }}"
       login_password: "{{ vault_exasol_admin_password }}"
       role: app_writer
       state: absent
       system_privileges:
         - CREATE SCHEMA
       object_privileges:
         - schema: app_schema
           object: fact_sales
           privileges:
             - INSERT
             - UPDATE

In check mode, ``exasol_grants`` still reads metadata but does not execute
planned ``GRANT`` or ``REVOKE`` statements. The result's ``executed_queries``
contains the statements that would run.

exasol_user
-----------

Use ``exasol.exasol.exasol_user`` to create, update, or remove one Exasol user.
User names are exact Exasol identifier values, including names that need
delimited-identifier syntax. A repeated ``state=present`` task is unchanged
when the user already exists, except when ``update_password=always`` is used:
Exasol cannot compare passwords, so this option always plans a password update
for an existing user and reports ``changed=true``.

``state=absent`` drops an existing user. It does not cascade by default;
specify ``cascade=true`` only when removing the user's dependent objects is
intended. LDAP distinguished names and passwords are sensitive and should come
from a protected secret source.

.. code-block:: yaml

   - name: Create an application user
     exasol.exasol.exasol_user:
       login_host: db.example.com
       login_user: "{{ vault_exasol_admin_user }}"
       login_password: "{{ vault_exasol_admin_password }}"
       name: app_user
       password: "{{ vault_app_user_password }}"

In check mode, the module reads user metadata and returns the planned SQL
without changing Exasol. Its ``exists`` value reports the predicted final
existence state and ``executed_queries`` contains the redacted planned SQL.

exasol_role
-----------

Use ``exasol.exasol.exasol_role`` to create or remove one Exasol role. The
module checks role metadata first, so repeated runs are idempotent. Role names
are exact Exasol identifier values, including names that need
delimited-identifier syntax.

``state=absent`` removes an existing role. It does not cascade by default;
set ``cascade=true`` only when removing dependent objects is intended.

.. code-block:: yaml

   - name: Create an application role
     exasol.exasol.exasol_role:
       login_host: db.example.com
       login_user: "{{ vault_exasol_admin_user }}"
       login_password: "{{ vault_exasol_admin_password }}"
       name: app_reader

In check mode, the module reads role metadata and returns the planned SQL
without changing Exasol. Its ``exists`` value reports the predicted final
existence state.

exasol_schema
-------------

Use ``exasol.exasol.exasol_schema`` to manage a physical schema and its
intrinsic metadata. ``state=present`` creates a missing schema and reconciles
only supplied ``new_name``, ``owner``, ``comment``, and ``raw_size_limit``
values. Omitted mutable properties remain unmanaged, and a repeated task that
already matches the requested state reports ``changed=false``.

``state=absent`` uses a non-cascading drop by default, so Exasol rejects the
operation for a non-empty schema. Set ``cascade=true`` only when deleting all
contained objects is intended.

.. code-block:: yaml

   - name: Create a reporting schema
     exasol.exasol.exasol_schema:
       login_host: db.example.com
       login_user: "{{ vault_exasol_admin_user }}"
       login_password: "{{ vault_exasol_admin_password }}"
       name: reporting
       owner: app_reader
       comment: Reporting data

In check mode, the module reads schema metadata and returns the same SQL plan
it would execute without changing Exasol. Its ``exists`` value reports the
predicted final existence state.
