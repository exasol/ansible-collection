# Exasol Ansible Collection

Automate Exasol database administration with Ansible.

## Installation

Installation and execution-environment setup are documented in the
[user guide](https://exasol.github.io/ansible-collection/main/user_guide.html).

## Quick start

Use the fully qualified collection name (FQCN) in a playbook. Supply
credentials from Ansible Vault or another secret manager rather than writing
them directly in the playbook:

```yaml
---
- name: Read Exasol metadata
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Get the Exasol server version
      exasol.exasol.exasol_query:
        login_host: db.example.com
        login_user: "{{ vault_exasol_user }}"
        login_password: "{{ vault_exasol_password }}"
        query: >-
          SELECT PARAM_VALUE
          FROM SYS.EXA_METADATA
          WHERE PARAM_NAME = 'databaseProductVersion'
```

See the [user guide](https://exasol.github.io/ansible-collection/main/user_guide.html)
for installation in execution environments, connection security, and examples
for every public module.
