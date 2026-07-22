#!/usr/bin/python
# Copyright: (c) 2026, Exasol AG <opensource@exasol.com>
# MIT License (see LICENSE or https://opensource.org/license/mit)

DOCUMENTATION = r"""
---
module: exasol_info
short_description: Gather basic Exasol server information
description:
  - Gathers basic Exasol server information through read-only metadata queries.
  - Returns the Exasol version, database name, and cluster size.
  - The module never changes Exasol state and always reports C(changed=false).
attributes:
  check_mode:
    description: Runs the same read-only metadata queries in check mode.
    support: full
version_added: "0.1.0"
author:
  - Exasol AG (@exasol)
extends_documentation_fragment:
  - exasol.exasol.connection
requirements:
  - exasol-ansible-modules
"""

EXAMPLES = r"""
---
- name: Gather Exasol server information
  exasol.exasol.exasol_info:
    login_host: db.example.com
    login_user: "{{ vault_exasol_user }}"
    login_password: "{{ vault_exasol_password }}"

- name: Gather Exasol server information in check mode
  exasol.exasol.exasol_info:
    login_host: db.example.com
    login_user: "{{ vault_exasol_user }}"
    login_password: "{{ vault_exasol_password }}"
  check_mode: true
"""

RETURN = r"""
version:
  description:
    - Exasol server version string returned by metadata.
  returned: always
  type: str
  sample: 8.38.0
database_name:
  description:
    - Exasol database name returned by metadata.
  returned: always
  type: str
  sample: EXA_DB
cluster_size:
  description:
    - Number of cluster nodes reported by Exasol metadata.
  returned: always
  type: int
  sample: 1
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.exasol.exasol.plugins.module_utils import (
    common_runtime_import,
)

common_runtime_import.make_source_runtime_importable_for_ansible_sanity(__file__)

from exasol.ansible_modules import exasol_info as exasol_info_utils


def main() -> None:
    """Run the Ansible module."""
    module = AnsibleModule(
        argument_spec=exasol_info_utils.module_argument_spec(),
        supports_check_mode=True,
    )

    params = module.params

    try:
        result = exasol_info_utils.run_info(
            params=params,
        )
    except ValueError as error:
        module.fail_json(
            msg=exasol_info_utils.sanitize_error_message(error, params=params)
        )
    except Exception as error:  # noqa: BLE001 - Ansible modules report all failures.
        module.fail_json(
            msg=exasol_info_utils.normalized_exasol_error_message(
                error,
                params=params,
                operation="Exasol info gathering",
            )
        )

    module.exit_json(**result)


if __name__ == "__main__":
    main()
