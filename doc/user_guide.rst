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
``ansible-navigator`` to run playbooks with that environment. This repository
provides execution-environment metadata in ``meta/execution-environment.yml``:

Add the collection to your execution-environment definition:

.. code-block:: yaml

   dependencies:
     galaxy:
       collections:
         - name: exasol.exasol

Then build the execution environment and run your playbook:

.. code-block:: bash

   ansible-builder build --tag exasol-ansible-ee --file execution-environment.yml
   ansible-navigator run playbook.yml --execution-environment-image exasol-ansible-ee

See the Ansible execution environment documentation for more details:
https://docs.ansible.com/projects/ansible/latest/getting_started_ee/introduction.html

If you do not use an execution environment, install
``exasol-ansible-modules`` for the configured ``ansible_python_interpreter`` on
the control node or remote host that executes the module.

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

Status: draft

Covers:
- scn~fully-qualified-collection-names-are-explained~1

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

exasol_info
-----------

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
