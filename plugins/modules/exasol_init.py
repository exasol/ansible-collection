#!/usr/bin/python
# Copyright: (c) 2026, Exasol AG <opensource@exasol.com>
# MIT License (see LICENSE or https://opensource.org/license/mit)

DOCUMENTATION = r"""
---
module: exasol_init
short_description: Initialize an Exasol environment (roles, users, grants, schemas, scripts)
description:
  - Orchestrates the roles, users, role grants, schemas, schema privilege
    grants, and init scripts needed to bring up a fresh Exasol environment
    in one Ansible task.
  - Reuses the same lifecycle logic as C(exasol_role), C(exasol_user), and
    the (unreleased) schema lifecycle helpers, so each item behaves exactly
    like the equivalent single-purpose module.
  - Executes in two passes so V(state=absent) and V(state=present) items can
    be mixed in one call - a teardown pass in reverse dependency order
    (schema grants, role grants, schemas, users, roles), followed by a
    reconciliation pass in forward dependency order (roles, users, role
    grants, schemas, schema grants, scripts).
  - Init scripts always run last, after every requested grant has been
    applied, and are executed as trusted-operator SQL with the same trust
    model as C(exasol_query) - they are not reconciled against existing
    state.
  - See C(specs/diagrams/exasol_init_process_diagram.md),
    C(specs/diagrams/exasol_init_domain_diagram.md), and
    C(specs/glossary/exasol_init_glossary.md) for the underlying domain
    model.
version_added: "0.2.0"
author:
  - Exasol AG (@exasol)
extends_documentation_fragment:
  - exasol.exasol.connection
options:
  roles:
    description: Roles to reconcile before everything else.
    type: list
    elements: dict
    default: []
    suboptions:
      name:
        description: Exact Exasol role identifier.
        type: str
        required: true
      state:
        description: Desired state of the role.
        type: str
        choices: [present, absent]
        default: present
      cascade:
        description: Add C(CASCADE) when dropping the role.
        type: bool
        default: false
  users:
    description: Users to reconcile alongside roles.
    type: list
    elements: dict
    default: []
    suboptions:
      name:
        description: Exact Exasol user identifier.
        type: str
        required: true
      password:
        description: Password used when creating the user or rotating it.
        type: str
      authentication_method:
        description: Authentication method for the user.
        type: str
        choices: [password, ldap]
      ldap_dn:
        description: LDAP distinguished name for O(users[].authentication_method=ldap).
        type: str
      state:
        description: Desired state of the user.
        type: str
        choices: [present, absent]
        default: present
      update_password:
        description: Password update behavior for an existing user.
        type: str
        choices: [always, on_create]
        default: on_create
      create_session:
        description: Grant C(CREATE SESSION) after creating a missing user.
        type: bool
        default: true
      cascade:
        description: Add C(CASCADE) when dropping the user.
        type: bool
        default: false
  role_grants:
    description: Role-to-user grants, applied once the role and user both exist.
    type: list
    elements: dict
    default: []
    suboptions:
      role:
        description: Exact Exasol role identifier to grant.
        type: str
        required: true
      user:
        description: Exact Exasol user identifier to grant the role to.
        type: str
        required: true
      state:
        description: Whether the grant should exist.
        type: str
        choices: [present, absent]
        default: present
  schemas:
    description: Schemas to reconcile, optionally reassigning the owner.
    type: list
    elements: dict
    default: []
    suboptions:
      name:
        description: Exasol schema identifier.
        type: str
        required: true
      owner:
        description: Exact Exasol user identifier to own the schema.
        type: str
      state:
        description: Desired state of the schema.
        type: str
        choices: [present, absent]
        default: present
      cascade:
        description: Add C(CASCADE) when dropping the schema.
        type: bool
        default: false
  grants:
    description: Schema-level privilege grants, applied once the schema and grantee both exist.
    type: list
    elements: dict
    default: []
    suboptions:
      schema:
        description: Exasol schema identifier the privilege applies to.
        type: str
        required: true
      privilege:
        description: Privilege to grant on the schema.
        type: str
        required: true
        choices: [ALL, ALTER, DELETE, EXECUTE, INDEX, INSERT, REFERENCES, SELECT, UPDATE]
      grantee:
        description: Exact Exasol user or role identifier receiving the privilege.
        type: str
        required: true
      state:
        description: Whether the grant should exist.
        type: str
        choices: [present, absent]
        default: present
  scripts:
    description:
      - Trusted-operator SQL statements executed last, after every requested
        grant has been applied.
      - Always executed (not reconciled), the same trust model as
        C(exasol_query).
    type: list
    elements: str
    default: []
requirements:
  - exasol-ansible-modules
"""

EXAMPLES = r"""
---
- name: Initialize a reporting environment
  exasol.exasol.exasol_init:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    roles:
      - name: REPORTER
    users:
      - name: REPORT_USER
        password: "{{ vault_report_user_password }}"
    role_grants:
      - role: REPORTER
        user: REPORT_USER
    schemas:
      - name: REPORT_SCHEMA
        owner: REPORT_USER
    grants:
      - schema: REPORT_SCHEMA
        privilege: SELECT
        grantee: REPORTER
    scripts:
      - CREATE TABLE REPORT_SCHEMA.EVENTS (ID INT)

- name: Tear down the same environment
  exasol.exasol.exasol_init:
    login_host: db.example.com
    login_user: "{{ vault_exasol_admin_user }}"
    login_password: "{{ vault_exasol_admin_password }}"
    grants:
      - schema: REPORT_SCHEMA
        privilege: SELECT
        grantee: REPORTER
        state: absent
    role_grants:
      - role: REPORTER
        user: REPORT_USER
        state: absent
    schemas:
      - name: REPORT_SCHEMA
        state: absent
        cascade: true
    users:
      - name: REPORT_USER
        state: absent
        cascade: true
    roles:
      - name: REPORTER
        state: absent
        cascade: true
"""

RETURN = r"""
executed_queries:
  description:
    - SQL statements executed by the module, in dependency order across all
      phases. Result redacts all secrets.
    - In check mode, this contains the statements that would be executed.
  returned: always
  type: list
  elements: str
roles:
  description: Per-item result for each entry in O(roles).
  returned: always
  type: list
  elements: dict
users:
  description: Per-item result for each entry in O(users).
  returned: always
  type: list
  elements: dict
role_grants:
  description: Per-item result for each entry in O(role_grants).
  returned: always
  type: list
  elements: dict
schemas:
  description: Per-item result for each entry in O(schemas).
  returned: always
  type: list
  elements: dict
grants:
  description: Per-item result for each entry in O(grants).
  returned: always
  type: list
  elements: dict
scripts:
  description: Aggregate result for O(scripts) execution.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.exasol.exasol.plugins.module_utils import (
    common_runtime_import,
)

common_runtime_import.make_source_runtime_importable_for_ansible_sanity(__file__)

from exasol.ansible_modules import exasol_init as exasol_init_utils


def main() -> None:
    """Run the Ansible module."""
    module = AnsibleModule(
        argument_spec=exasol_init_utils.module_argument_spec(),
        supports_check_mode=True,
    )

    params = module.params

    try:
        result = exasol_init_utils.run_init(params, check_mode=module.check_mode)
    except ValueError as error:
        module.fail_json(msg=exasol_init_utils.sanitize_error_message(error, params))
    except Exception as error:  # noqa: BLE001 - Ansible modules report all failures.
        module.fail_json(
            msg=exasol_init_utils.normalized_exasol_error_message(
                error,
                params=params,
                operation="Exasol environment initialization",
            )
        )

    module.exit_json(**result)


if __name__ == "__main__":
    main()
