# Exasol Ansible Collection

Ansible Collection for automating Exasol database operations.

## Installation

Installation and execution-environment setup are documented in the
[user guide](https://exasol.github.io/ansible-collection/main/user_guide.html).

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

The collection is currently a skeleton. Add module-specific tasks once public
modules are available.
