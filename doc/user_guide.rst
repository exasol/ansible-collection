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

The collection is currently a skeleton. A playbook can already declare the
collection dependency, but module-specific tasks should be added once public
modules are available:

.. code-block:: yaml

   ---
   - name: Prepare Exasol hosts
     hosts: all
     collections:
       - exasol.exasol
     tasks:
       - name: Verify the collection is available
         ansible.builtin.debug:
           msg: "Exasol collection is installed."
