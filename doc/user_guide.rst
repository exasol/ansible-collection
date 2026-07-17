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
