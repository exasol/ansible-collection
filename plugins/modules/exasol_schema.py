#!/usr/bin/python
# Copyright: (c) 2026, Exasol AG <opensource@exasol.com>
# MIT License (see LICENSE or https://opensource.org/license/mit)

DOCUMENTATION = r"""
---
module: exasol_schema
short_description: Manage Exasol database schemas
description:
  - Creates, renames, updates, and drops physical Exasol schemas.
  - Schema metadata is checked before executing DDL.
  - Omitted mutable properties remain unmanaged.
  - Dropping schemas can optionally use CASCADE.
version_added: "0.1.0"
author:
  - Exasol AG (@exasol)
extends_documentation_fragment:
  - exasol.exasol.connection
options:
  name:
    description:
     - Name of the Exasol schema to manage.
     - Treated as an exact Exasol identifier value.
     - Case and special characters are preserved
       by rendering the name as a delimited SQL identifier.
     - Delimited-identifier syntax is also accepted
       and normalized to the same exact identifier value.
    type: str
    required: true
    aliases:
      - schema
  state:
    description:
      - Desired state of the Exasol schema.
      - V(present) creates the schema if it does not exist.
      - V(absent) removes the schema if it exists.
    type: str
    choices:
      - present
      - absent
    default: present
  cascade:
    description:
      - Add C(CASCADE) when dropping an existing schema.
      - Required when dropping schemas that contain database objects.
    type: bool
    default: false
  owner:
    description:
      - User or role that should own the schema.
      - Ownership is assigned with C(ALTER SCHEMA ... CHANGE OWNER) after
        creation and is reconciled only when this option is provided.
    type: str
  comment:
    description:
      - Comment assigned to the schema.
      - An empty value removes an existing comment; an omitted value leaves the
        comment unmanaged.
    type: str
  new_name:
    description:
      - Desired final name of the schema.
      - If O(name) is missing and O(new_name) already exists, the rename is
        considered complete.
    type: str
  raw_size_limit:
    description:
      - Maximum raw size of the schema in bytes.
      - Must be a non-negative integer and is reconciled only when provided.
    type: int
requirements:
  - exasol-ansible-modules
"""

EXAMPLES = r"""
---
- name: Create an Exasol schema
  exasol.exasol.exasol_schema:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: sales

- name: Create schema with exact identifier semantics
  exasol.exasol.exasol_schema:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: '"Sales Reporting"'

- name: Drop an empty Exasol schema
  exasol.exasol.exasol_schema:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: sales
    state: absent

- name: Create a schema and assign it to a role
  exasol.exasol.exasol_schema:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: sales
    owner: reporting_role
    comment: Sales reporting schema
    raw_size_limit: 134217728

- name: Rename an Exasol schema
  exasol.exasol.exasol_schema:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: old_sales
    new_name: sales

- name: Drop an Exasol schema and all contained objects
  exasol.exasol.exasol_schema:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: sales
    state: absent
    cascade: true
"""

RETURN = r"""
schema:
  description:
    - Exact Exasol schema name targeted by the module.
    - The value preserves case and special characters after parsing optional
      delimited-identifier syntax.
  returned: always
  type: str
  sample: Sales+/=Schema
state:
  description:
    - Requested state.
  returned: always
  type: str
  sample: present
exists:
  description:
    - Whether the schema exists after the module action, or would exist in
      check mode.
  returned: always
  type: bool
  sample: true
executed_queries:
  description:
    - SQL statements that were executed by the module.
    - In check mode, this contains the statements that would be executed.
  returned: always
  type: list
  elements: str
  sample:
    - CREATE SCHEMA "Sales+/=Schema"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.exasol.exasol.plugins.module_utils import common_runtime_import

common_runtime_import.make_source_runtime_importable_for_ansible_sanity(__file__)

from exasol.ansible_modules import exasol_schema as exasol_schema_utils


def main() -> None:
    """Run the Ansible module."""
    module = AnsibleModule(
        argument_spec=exasol_schema_utils.module_argument_spec(),
        supports_check_mode=True,
    )

    params = module.params

    try:
        result = exasol_schema_utils.run_schema(params, check_mode=module.check_mode)
    except ValueError as error:
        module.fail_json(msg=exasol_schema_utils.sanitize_error_message(error, params))
    except Exception as error:  # noqa: BLE001 - Ansible modules report all failures.
        module.fail_json(
            msg=exasol_schema_utils.normalized_exasol_error_message(
                error, params=params, operation="Exasol schema management"
            )
        )

    module.exit_json(**result)


if __name__ == "__main__":
    main()
