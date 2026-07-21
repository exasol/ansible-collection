Getting Started With An Execution Environment
==============================================

An execution environment packages Ansible, this collection, and its Python
runtime dependencies into one container image. This avoids installing runtime
packages on every control node. The following minimal project uses
``ansible-builder`` to create that image and ``ansible-navigator`` to run a
read-only playbook.

Create a Project
----------------

Create an empty directory containing these files:

.. code-block:: text

   exasol-automation/
   ├── ansible.cfg
   ├── execution-environment.yml
   ├── group_vars/all/exasol_vault.yml
   ├── inventory/hosts.yml
   └── test_playbook.yml

The examples use Podman, but another container runtime supported by
``ansible-builder`` and ``ansible-navigator`` can be configured instead.

Create ``ansible.cfg`` so the command examples use the project's inventory:

.. code-block:: ini

   [defaults]
   inventory = inventory/hosts.yml
   show_custom_stats = true

Define The Execution Environment
--------------------------------

Create ``execution-environment.yml``. Pin collection and Ansible versions in a
production project after testing the combination.

.. code-block:: yaml

   ---
   version: 3

   images:
     base_image:
       name: registry.fedoraproject.org/fedora:44

   dependencies:
     python_interpreter:
       package_system: python3
     ansible_core:
       package_pip: ansible-core==2.21.2
     ansible_runner:
       package_pip: ansible-runner==2.4.3
     galaxy:
       collections:
         - name: exasol.exasol
           version: 0.3.0

Create An Inventory And Playbook
--------------------------------

Create ``inventory/hosts.yml`` and replace the example host. The collection
modules run locally in the execution environment and connect to Exasol through
their ``login_*`` arguments.

.. code-block:: yaml

   ---
   all:
     children:
       exasol_databases:
         hosts:
           db.example.com:
             exasol_login_port: 8563
         vars:
           # Exasol modules connect using their login_* arguments; execute them on
           # the Ansible controller rather than SSHing to the database endpoint.
           ansible_connection: local
           ansible_python_interpreter: "{{ ansible_playbook_python }}"

Store the login values in an encrypted
``group_vars/all/exasol_vault.yml`` file. Do not commit the unencrypted file or
the vault password.

.. code-block:: yaml

   ---
   vault_exasol_login_user: exasol_user
   vault_exasol_login_password: change-this-password

Create ``test_playbook.yml``. It uses module defaults for the shared
connection settings and runs only read-only operations.

.. code-block:: yaml

   ---
   - name: Read-only demo for the Exasol collection
     hosts: exasol_databases
     gather_facts: false
     collections:
       - exasol.exasol
     vars_files:
       - group_vars/all/exasol_vault.yml
     module_defaults:
       group/exasol.exasol.connection:
         login_host: "{{ inventory_hostname }}"
         login_port: "{{ exasol_login_port }}"
         login_user: "{{ vault_exasol_login_user }}"
         login_password: "{{ vault_exasol_login_password }}"
         validate_certs: true
     tasks:
       - name: Gather Exasol server information
         exasol_info:
         register: exasol_info

       - name: Store Exasol server information as statistics
         ansible.builtin.set_stats:
           data:
             exasol_server_information: "{{ exasol_info }}"
             exasol_server_version: "{{ exasol_info.version }}"
             exasol_database_name: "{{ exasol_info.database_name }}"
             exasol_cluster_size: "{{ exasol_info.cluster_size }}"
           aggregate: false
           per_host: true

       - name: Read the current Exasol session user and timestamp
         exasol_query:
           query: >-
             SELECT CURRENT_USER AS CONNECTED_USER,
                    CURRENT_TIMESTAMP AS EXECUTED_AT
         register: demo_query

       - name: Store the query result as statistics
         ansible.builtin.set_stats:
           data:
             exasol_session_information: "{{ demo_query.query_result }}"
           aggregate: false
           per_host: true

Store ``vault_exasol_login_user`` and ``vault_exasol_login_password`` in the
encrypted vault file. Do not include secret values in ``exasol_query.query``:
supplied SQL is returned in ``executed_queries``. See the Ansible `Vault guide
<https://docs.ansible.com/projects/ansible/latest/vault_guide/vault.html>`_ for
how to create and use encrypted variable files.

Build And Run
-------------

Install ``ansible-builder`` and ``ansible-navigator`` on the machine that
builds and launches the image. From the project directory, build the image,
check the playbook syntax, and run it:

.. code-block:: bash

   ansible-builder build --tag exasol-ee --file execution-environment.yml
   ansible-navigator run test_playbook.yml \
     --execution-environment-image exasol-ee \
     --mode stdout --pull-policy missing

Use ``ansible-navigator``'s normal vault-password and inventory options for
your chosen secret-management and inventory setup. For further module-specific
examples, see the :doc:`user guide <user_guide>`. For more information about
execution environments, see the Ansible `Execution Environments getting
started guide <https://docs.ansible.com/projects/ansible/latest/getting_started_ee/index.html>`_.
