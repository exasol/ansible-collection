# Exasol Ansible Collection

Ansible Collection for automating Exasol database operations.

## Installation

Installation and execution-environment setup are documented in the
[user guide](doc/user_guide.rst).

## Development

To build the collection archive locally:

```bash
poetry run nox -s collection:build
```

Run the Ansible collection sanity checks with:

```bash
poetry run nox -s collection:sanity
```

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

The collection currently provides public modules for direct SQL execution and
basic Exasol administration:

* `exasol.exasol.exasol_query`
* `exasol.exasol.exasol_user`
* `exasol.exasol.exasol_role`

See the [user guide](doc/user_guide.rst) for module-specific examples and
execution-environment setup.
