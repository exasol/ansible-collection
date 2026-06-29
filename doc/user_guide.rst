User Guide
==========

Installation
------------

The collection is not published to Ansible Galaxy yet. To try the current
checkout locally, build the collection archive and install that archive:

.. code-block:: bash

   poetry run nox -s collection:build
   poetry run ansible-galaxy collection install --force .build_output/collections/exasol-exasol-*.tar.gz

After the collection is published, install it by collection name:

.. code-block:: bash

   ansible-galaxy collection install exasol.exasol

Runtime Dependencies
--------------------

Install the Python dependencies required by collection modules in the execution
environment that runs Ansible:

.. code-block:: bash

   python -m pip install -r requirements.txt

The dependency list includes ``exasol-ansible-modules``, the Python package with
the Exasol module runtime logic.

Basic Playbook
--------------

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
