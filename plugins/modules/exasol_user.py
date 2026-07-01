#!/usr/bin/python
# Copyright: (c) 2026, Exasol AG <opensource@exasol.com>
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: exasol_user
short_description: Manage Exasol database users
description:
  - Creates, updates, and drops Exasol database users using pyexasol.
  - User names are restricted to conservative SQL identifiers
    (letters, digits, underscore) and are normalized to Exasol's
    case-insensitive uppercase form for idempotent operations.
  - This restriction ensures predictable Ansible idempotency and avoids
    ambiguity between quoted and unquoted Exasol identifiers.
  - Quoted or special-character user names are not supported by this module
    in order to maintain consistent behavior across environments.
  - This restriction may be revised in the future; see
      https://github.com/exasol/ansible-collection/issues/38
  - Passwords are quoted for Exasol's C(IDENTIFIED BY) syntax and are never
    returned in module results.
  - LDAP-authenticated users use Exasol's C(IDENTIFIED AT LDAP AS) syntax.
version_added: "0.1.0"
author:
  - Exasol AG (@exasol)
extends_documentation_fragment:
  - exasol.exasol.connection
options:
  name:
    description:
      - Name of the Exasol user to manage.
    type: str
    required: true
    aliases:
      - user
  password:
    description:
      - Password used when creating the user or when O(update_password=always).
      - Required when the user has to be created with
        O(authentication_method=password).
    type: str
  authentication_method:
    description:
      - Authentication method to configure when creating or updating the user.
      - If omitted, V(ldap) is inferred when O(ldap_dn) is set; otherwise
        V(password) is used.
    type: str
    choices:
      - password
      - ldap
  ldap_dn:
    description:
      - LDAP distinguished name used when O(authentication_method=ldap).
      - This value is treated as sensitive in error messages and redacted from
        generated SQL returned in module results.
    type: str
  state:
    description:
        - Desired state of the Exasol user.
        - V(present) creates the user if it does not exist and applies any requested updates.
        - V(absent) removes the user if it exists.
    type: str
    choices:
      - present
      - absent
    default: present
  update_password:
    description:
      - V(on_create) sets the password only when creating a missing user.
      - V(always) changes the password for an existing user on every run.
      - Exasol does not expose a reversible password comparison, so V(always)
        reports C(changed=true) whenever the user exists.
    type: str
    choices:
      - always
      - on_create
    default: on_create
  create_session:
    description:
      - Grant C(CREATE SESSION) after creating a missing user.
      - The grant is only executed together with user creation.
    type: bool
    default: true
  cascade:
    description:
      - Add C(CASCADE) when dropping an existing user.
    type: bool
    default: false
requirements:
  - exasol-ansible-modules
"""

EXAMPLES = r"""
---
- name: Create an Exasol user
  exasol.exasol.exasol_user:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: app_user
    password: "{{ vault_app_user_password }}"

- name: Rotate an existing Exasol user password
  exasol.exasol.exasol_user:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: app_user
    password: "{{ vault_new_app_user_password }}"
    update_password: always

- name: Switch an existing user to LDAP authentication
  exasol.exasol.exasol_user:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: app_user
    authentication_method: ldap
    ldap_dn: cn=app_user,dc=authorization,dc=exasol,dc=com

- name: Drop an Exasol user and owned schemas
  exasol.exasol.exasol_user:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    name: app_user
    state: absent
    cascade: true
"""

RETURN = r"""
user:
  description:
    - Normalized Exasol user name.
    - The value is converted to Exasol's canonical form, which means it is
      uppercased and used in a consistent format for idempotent operations.
      This ensures that different input forms (e.g. mixed or lowercase) are
      treated as the same database user.
    - Quoted or special-character user names are not supported by this module
      in order to maintain consistent behavior across environments.
    - This behavior may be revised in the future; see
      https://github.com/exasol/ansible-collection/issues/38
  returned: always
  type: str
  sample: APP_USER
state:
  description:
    - Requested state.
  returned: always
  type: str
  sample: present
exists:
  description:
    - Whether the user exists after the module action, or would exist in check
      mode.
  returned: always
  type: bool
  sample: true
executed_queries:
  description:
    - SQL statements that were executed by the module. Result redacts all secrets.
    - In check mode, this contains the statements that would be executed.
  returned: always
  type: list
  elements: str
  sample:
    - CREATE USER "APP_USER" IDENTIFIED BY "********"
"""

from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.exasol.exasol.plugins.module_utils import (
    common_runtime_import,
)

common_runtime_import.make_source_runtime_importable_for_ansible_sanity(__file__)

from exasol.ansible_modules import common_query
from exasol.ansible_modules import exasol_query as exasol_query_utils
from exasol.ansible_modules import exasol_user as exasol_user_utils


def main() -> None:
    """Run the Ansible module."""
    argument_spec = {
        **exasol_query_utils.exasol_connection_argument_spec(),
        "name": {"type": "str", "required": True, "aliases": ["user"]},
        "password": {"type": "str", "no_log": True},
        "authentication_method": {
            "type": "str",
            "choices": ["password", "ldap"],
        },
        "ldap_dn": {"type": "str", "no_log": True},
        "state": {
            "type": "str",
            "choices": ["present", "absent"],
            "default": "present",
        },
        "update_password": {
            "type": "str",
            "choices": ["always", "on_create"],
            "default": "on_create",
            "no_log": False,
        },
        "create_session": {"type": "bool", "default": True},
        "cascade": {"type": "bool", "default": False},
    }
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    params = module.params

    try:
        result = run_user(params, check_mode=module.check_mode)
    except ValueError as error:
        module.fail_json(msg=exasol_user_utils.sanitize_error_message(error, params))
    except Exception as error:  # noqa: BLE001 - Ansible modules report all failures.
        module.fail_json(
            msg=exasol_user_utils.normalized_exasol_error_message(
                error,
                params=params,
                operation="Exasol user management",
            )
        )

    module.exit_json(**result)


def run_user(params: dict[str, Any], check_mode: bool = False) -> dict[str, object]:
    """Connect to Exasol and manage the requested user."""
    with common_query.connect_to_exasol(
        params,
        module_name="exasol_user",
    ) as connection:
        return exasol_user_utils.ensure_user(
            connection,
            params,
            check_mode=check_mode,
        )


if __name__ == "__main__":
    main()
