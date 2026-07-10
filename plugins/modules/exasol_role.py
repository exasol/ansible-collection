#!/usr/bin/python
# Copyright: (c) 2026, Exasol AG <opensource@exasol.com>
# MIT License (see LICENSE or https://opensource.org/license/mit)

DOCUMENTATION = r"""
---
module: exasol_role
short_description: Manage Exasol database roles
description:
  - Creates and drops Exasol database roles using pyexasol.
  - Role names are treated as exact Exasol identifier values.
  - The module preserves case and special characters by rendering role names
    as delimited SQL identifiers.
  - Values that are already written using Exasol's delimited-identifier syntax
    are accepted and normalized to the same exact identifier value.
version_added: "0.1.0"
author:
  - Exasol AG (@exasol)
extends_documentation_fragment:
  - exasol.exasol.connection
options:
  name:
    description:
      - Name of the Exasol role to manage.
      - This value is used exactly as provided when the module generates SQL.
    type: str
    required: true
    aliases:
      - role
  state:
    description:
      - Whether the role should exist.
    type: str
    choices:
      - present
      - absent
    default: present
  cascade:
    description:
      - Add C(CASCADE) when dropping an existing role.
    type: bool
    default: false
requirements:
  - exasol-ansible-modules
"""

EXAMPLES = r"""
---
- name: Create an Exasol role
  exasol.exasol.exasol_role:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: app_role

- name: Drop an Exasol role
  exasol.exasol.exasol_role:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: app_role
    state: absent
"""

RETURN = r"""
role:
  description:
    - Exact Exasol role name targeted by the module.
  returned: always
  type: str
  sample: App+/=Role
state:
  description:
    - Requested state.
  returned: always
  type: str
  sample: present
exists:
  description:
    - Whether the role exists after the module action, or would exist in check
      mode.
  returned: always
  type: bool
  sample: true
executed_queries:
  description:
    - SQL statements executed by the module.
    - In check mode, this contains the statements that would be executed.
  returned: always
  type: list
  elements: str
  sample:
    - CREATE ROLE "App+/=Role"
"""

from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.exasol.exasol.plugins.module_utils import (
    common_runtime_import,
)

common_runtime_import.make_source_runtime_importable_for_ansible_sanity(__file__)

from exasol.ansible_modules import common_query
from exasol.ansible_modules import exasol_role as exasol_role_utils


def main() -> None:
    """Run the Ansible module."""
    argument_spec = {
        **common_query.exasol_connection_argument_spec(),
        "name": {"type": "str", "required": True, "aliases": ["role"]},
        "state": {
            "type": "str",
            "choices": ["present", "absent"],
            "default": "present",
        },
        "cascade": {"type": "bool", "default": False},
    }
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    params = module.params

    try:
        result = run_role(params, check_mode=module.check_mode)
    except ValueError as error:
        module.fail_json(msg=exasol_role_utils.sanitize_error_message(error, params))
    except Exception as error:  # noqa: BLE001 - Ansible modules report all failures.
        module.fail_json(
            msg=exasol_role_utils.normalized_exasol_error_message(
                error,
                params=params,
                operation="Exasol role management",
            )
        )

    module.exit_json(**result)


def run_role(params: dict[str, Any], check_mode: bool = False) -> dict[str, object]:
    """Connect to Exasol and manage the requested role."""
    with common_query.connect_to_exasol(
        params,
        module_name="exasol_role",
    ) as connection:
        return exasol_role_utils.ensure_role(
            connection,
            params,
            check_mode=check_mode,
        )


if __name__ == "__main__":
    main()
