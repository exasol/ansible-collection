#!/usr/bin/python
# Copyright: (c) 2026, Exasol AG <opensource@exasol.com>
# MIT License (see LICENSE or https://opensource.org/license/mit)

DOCUMENTATION = r"""
---
module: exasol_grants
short_description: Manage Exasol database grants
description:
  - Grants or revokes requested Exasol privileges for one user or role.
  - The module is idempotent and uses Exasol privilege metadata before
    generating C(GRANT) or C(REVOKE) statements.
  - Supported principals are users and roles, selected with exactly one of
    O(user) or O(role).
  - Supported grant targets are direct system privileges, schema-level object
    privileges, schema-qualified object privileges, and role memberships.
  - O(admin_option) can grant system privileges and role memberships with
    C(WITH ADMIN OPTION).
  - User and role names are treated as exact Exasol identifier values.
  - Schema and object names use the collection's conservative regular
    identifier validation.
  - This module does not manage connection object grants, exclusive
    reconciliation, or broad C(ALL PRIVILEGES) requests.
  - At least one of O(system_privileges), O(roles), or O(object_privileges) is
    required.
attributes:
  check_mode:
    description: Can predict grant changes without modifying Exasol.
    support: full
version_added: "0.3.0"
author:
  - Exasol AG (@exasol)
extends_documentation_fragment:
  - exasol.exasol.connection
options:
  user:
    description:
      - Exasol user that should receive or lose the requested privileges.
      - Exactly one of O(user) or O(role) is required.
      - The value is used as an exact Exasol identifier.
    type: str
  role:
    description:
      - Exasol role that should receive or lose the requested privileges.
      - Exactly one of O(user) or O(role) is required.
      - The value is used as an exact Exasol identifier.
    type: str
  state:
    description:
      - Whether the requested privileges should be present or absent.
      - V(absent) revokes only the privileges listed in this task.
    type: str
    choices:
      - present
      - absent
    default: present
  system_privileges:
    description:
      - Direct system privileges to grant or revoke, for example
        C(CREATE SESSION) or C(USE ANY SCHEMA).
      - Each item may be a privilege name string, or a dictionary with
        C(privilege) and optional C(admin_option).
      - String items use the task-level O(admin_option) value.
      - Dictionary C(admin_option) values override the task-level
        O(admin_option) value for that system privilege.
      - Must not be empty when supplied.
      - Supported values are C(ACCESS ANY CONNECTION),
        C(ALTER ANY CONNECTION), C(ALTER ANY SCHEMA), C(ALTER ANY TABLE),
        C(ALTER ANY VIRTUAL SCHEMA), C(ALTER ANY VIRTUAL SCHEMA REFRESH),
        C(ALTER SYSTEM), C(ALTER USER), C(CREATE ANY FUNCTION),
        C(CREATE ANY SCRIPT), C(CREATE ANY TABLE), C(CREATE ANY VIEW),
        C(CREATE CONNECTION), C(CREATE FUNCTION), C(CREATE ROLE),
        C(CREATE SCHEMA), C(CREATE SCRIPT), C(CREATE SESSION),
        C(CREATE TABLE), C(CREATE USER), C(CREATE VIEW),
        C(CREATE VIRTUAL SCHEMA), C(DELETE ANY TABLE),
        C(DROP ANY CONNECTION), C(DROP ANY FUNCTION), C(DROP ANY ROLE),
        C(DROP ANY SCHEMA), C(DROP ANY SCRIPT), C(DROP ANY TABLE),
        C(DROP ANY VIEW), C(DROP ANY VIRTUAL SCHEMA), C(DROP USER),
        C(EXECUTE ANY FUNCTION), C(EXECUTE ANY SCRIPT), C(EXPORT),
        C(GRANT ANY CONNECTION), C(GRANT ANY OBJECT PRIVILEGE),
        C(GRANT ANY PRIVILEGE), C(GRANT ANY ROLE),
        C(IMPERSONATE ANY USER), C(IMPORT), C(INSERT ANY TABLE),
        C(KILL ANY SESSION), C(MANAGE CONSUMER GROUPS),
        C(SELECT ANY DICTIONARY), C(SELECT ANY TABLE),
        C(SET ANY CONSUMER GROUP), C(UPDATE ANY TABLE), C(USE ANY CONNECTION),
        and C(USE ANY SCHEMA).
    type: list
    elements: raw
  roles:
    description:
      - Roles to grant to or revoke from the selected O(user) or O(role).
      - Each item may be a role name string, or a dictionary with C(role) and
        optional C(admin_option).
      - String items use the task-level O(admin_option) value.
      - Dictionary C(admin_option) values override the task-level
        O(admin_option) value for that role membership.
      - Role memberships are reconciled through C(EXA_DBA_ROLE_PRIVS).
      - Must not be empty when supplied.
    type: list
    elements: raw
  admin_option:
    description:
      - Whether system privileges and role memberships should be granted with
        C(WITH ADMIN OPTION).
      - If omitted or V(false), C(WITH ADMIN OPTION) is not used.
      - Applies only to O(system_privileges) and O(roles), not object
        privileges.
      - Individual O(system_privileges) and O(roles) dictionary entries can
        override this value.
      - When V(false), an existing system privilege or role membership with
        admin option is reconciled by revoking and re-granting it without admin
        option.
    type: bool
    default: false
  object_privileges:
    description:
      - Schema-scoped object privileges to grant or revoke.
      - Must not be empty when supplied.
    type: list
    elements: dict
    suboptions:
      schema:
        description:
          - Schema that contains the privilege target.
          - When O(object_privileges[].object) is omitted, the privilege targets
            the schema itself.
        type: str
        required: true
      object:
        description:
          - Optional object name inside O(object_privileges[].schema).
        type: str
      object_type:
        description:
          - Optional object type rendered before the qualified object name.
          - Omit this for schema-level grants and ordinary table grants.
        type: str
        choices:
          - function
          - script
          - table
          - view
          - virtual_schema
      privileges:
        description:
          - Object privilege names to grant or revoke, for example C(USAGE) or
            C(SELECT).
          - Supported values are C(ACCESS), C(ALTER), C(DELETE), C(EXECUTE),
            C(IMPERSONATION), C(INSERT), C(REFERENCES), C(REFRESH),
            C(SELECT), C(UPDATE), and C(USAGE).
        type: list
        elements: str
        required: true
requirements:
  - exasol-ansible-modules
"""

EXAMPLES = r"""
---
- name: Grant a system privilege to a user
  exasol.exasol.exasol_grants:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    user: app_user
    system_privileges:
      - CREATE SESSION

- name: Grant schema usage to a role
  exasol.exasol.exasol_grants:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    role: app_reader
    object_privileges:
      - schema: app_schema
        privileges:
          - USAGE

- name: Grant mixed system privileges with per-privilege admin option
  exasol.exasol.exasol_grants:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    role: security_admin
    system_privileges:
      - privilege: SELECT ANY TABLE
        admin_option: true
      - privilege: CREATE SESSION
        admin_option: false

- name: Grant a role membership to a user
  exasol.exasol.exasol_grants:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    user: app_user
    roles:
      - app_reader

- name: Grant a role membership with admin option
  exasol.exasol.exasol_grants:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    user: app_user
    roles:
      - app_reader
    admin_option: true

- name: Grant mixed role memberships with per-role admin option
  exasol.exasol.exasol_grants:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    user: app_user
    roles:
      - role: app_reader
        admin_option: true
      - role: app_writer
        admin_option: false

- name: Revoke select on one table from a user
  exasol.exasol.exasol_grants:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    user: app_user
    state: absent
    object_privileges:
      - schema: app_schema
        object: fact_sales
        privileges:
          - SELECT
"""

RETURN = r"""
principal:
  description:
    - Exact Exasol user or role name targeted by the module.
  returned: always
  type: str
  sample: app_user
principal_type:
  description:
    - Type of principal selected by the task.
  returned: always
  type: str
  sample: user
state:
  description:
    - Requested grant state.
  returned: always
  type: str
  sample: present
executed_queries:
  description:
    - Privilege-changing SQL statements executed by the module.
    - In check mode, this contains the statements that would be executed.
  returned: always
  type: list
  elements: str
  sample:
    - GRANT CREATE SESSION TO "app_user"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.exasol.exasol.plugins.module_utils import (
    common_runtime_import,
)

common_runtime_import.make_source_runtime_importable_for_ansible_sanity(__file__)

from exasol.ansible_modules import exasol_grants as exasol_grants_utils


def main() -> None:
    """Run the Ansible module."""
    module = AnsibleModule(
        argument_spec=exasol_grants_utils.module_argument_spec(),
        supports_check_mode=True,
        required_one_of=[("user", "role")],
        mutually_exclusive=[("user", "role")],
    )

    params = module.params

    try:
        result = exasol_grants_utils.run_grants(params, check_mode=module.check_mode)
    except ValueError as error:
        module.fail_json(msg=exasol_grants_utils.sanitize_error_message(error, params))
    except Exception as error:  # noqa: BLE001 - Ansible modules report all failures.
        module.fail_json(
            msg=exasol_grants_utils.normalized_exasol_error_message(
                error,
                params=params,
                operation="Exasol grant management",
            )
        )

    module.exit_json(**result)


if __name__ == "__main__":
    main()
