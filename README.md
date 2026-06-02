# Exasol Ansible Collection

Ansible Collection for automating Exasol database operations.

## Installation

The collection is not published to Ansible Galaxy yet.
To try it locally, build the collection archive from this checkout and install that archive:

```bash
poetry run nox -s collection:build
poetry run ansible-galaxy collection install --force dist/exasol-exasol-*.tar.gz
```

Run the Ansible collection sanity checks with:

```bash
poetry run nox -s collection:sanity
```

After the collection is published, installation will use the Galaxy collection
name:

```bash
ansible-galaxy collection install exasol.exasol
```

## Runtime Dependencies

Install the Python dependencies required by the collection modules in the
execution environment that runs Ansible:

```bash
python -m pip install -r requirements.txt
```

The dependency list includes `pyexasol`, which modules can use for Exasol
database access, and `pyproject`, which modules can use for project metadata.

## Usage

Use the collection from a playbook with the fully qualified collection name:

```yaml
---
- name: Prepare Exasol hosts
  hosts: all
  collections:
    - exasol.exasol
  tasks:
    - name: Verify the collection is available
      ansible.builtin.debug:
        msg: "Exasol collection is installed."
```

The collection is currently a skeleton. Add module-specific tasks once public
modules are available.
