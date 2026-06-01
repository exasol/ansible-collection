# Exasol Ansible Collection

Ansible Collection for installing Exasol.

## Installation

The collection is not published to Ansible Galaxy yet.
To try it locally, build the collection archive from this checkout and install that archive:

```bash
ansible-galaxy collection build --force --output-path dist .
ansible-galaxy collection install --force dist/exasol-ansible_collection-*.tar.gz
```

## Runtime Dependencies

Install the Python dependencies required by the collection modules in the
execution environment that runs Ansible:

```bash
python -m pip install -r requirements.txt
```

The dependency list includes `pyexasol`, which modules can use for Exasol
database access.

## Usage

Use the collection from a playbook with the fully qualified collection name:

```yaml
---
- name: Install Exasol
  hosts: all
  collections:
    - exasol.ansible_collection
  tasks:
    - name: Placeholder task
      ansible.builtin.debug:
        msg: "Replace this task with Exasol installation automation."
```
