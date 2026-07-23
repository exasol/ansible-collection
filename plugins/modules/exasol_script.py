#!/usr/bin/python
# Copyright: (c) 2026, Exasol AG <opensource@exasol.com>
# MIT License (see LICENSE or https://opensource.org/license/mit)

DOCUMENTATION = r"""
---
module: exasol_script
short_description: Execute a multi-statement SQL script against Exasol
description:
  - Executes a SQL script containing one or more statements against an
    Exasol database using pyexasol's C(execute_sql_script) capability.
  - The script is split into statements before execution. Semicolons inside
    string literals, quoted SQL identifiers, line comments, block comments,
    and Exasol script bodies do not terminate statements. Exasol script
    bodies, such as C(CREATE ... SCRIPT) bodies, are terminated by a
    standalone C(/) line.
  - Statements execute in order on one connection. If a statement fails, the
    original error is raised and later statements do not execute.
  - A script made up only of read-only statements reports C(changed=false).
    A script containing any DDL or DML statement reports C(changed=true).
  - SQL supplied through O(script) is returned in C(executed_queries). Do not
    include passwords, tokens, or other secrets in query text.
attributes:
  check_mode:
    description: Executes read-only SQL and predicts writable SQL without modifying Exasol.
    support: full
version_added: "0.4.0"
author:
  - Exasol AG (@exasol)
extends_documentation_fragment:
  - exasol.exasol.connection
options:
  script:
    description:
      - SQL script text containing one or more statements.
      - Unlike the M(exasol.exasol.exasol_query) module's C(query) option,
        this is always a single string, never a list, and does not accept
        positional or named arguments; pyexasol does not support bound
        parameters for scripts.
      - Do not include passwords, tokens, or other secrets because this value
        is returned in C(executed_queries).
    type: str
    required: true
requirements:
  - exasol-ansible-modules
  - pyexasol>=2.3.0
"""

EXAMPLES = r"""
---
- name: Run a batch of statements as one script
  exasol.exasol.exasol_script:
    login_host: db.example.com
    login_user: "{{ vault_exasol_user }}"
    login_password: "{{ vault_exasol_password }}"
    login_schema: reporting
    script: |
      CREATE SCHEMA IF NOT EXISTS demo;
      CREATE OR REPLACE TABLE demo.t (id DECIMAL(18,0));
      INSERT INTO demo.t VALUES (1);

- name: Create a Python UDF script whose body contains semicolons
  exasol.exasol.exasol_script:
    login_host: db.example.com
    login_user: "{{ vault_exasol_user }}"
    login_password: "{{ vault_exasol_password }}"
    script: |
      CREATE OR REPLACE PYTHON3 SCALAR SCRIPT demo.double_value(x DOUBLE)
      RETURNS DOUBLE AS
      def run(ctx):
          x = ctx.x; return x * 2
      /

- name: Run a read-only script in check mode
  exasol.exasol.exasol_script:
    login_host: db.example.com
    login_user: "{{ vault_exasol_user }}"
    login_password: "{{ vault_exasol_password }}"
    script: |
      SELECT 1;
      SELECT 2;
  check_mode: true
"""

RETURN = r"""
query_result:
  description:
    - Rows returned by the last statement.
    - Empty for statements without a result set.
  returned: always
  type: list
  elements: dict
  sample:
    - A: 1
query_all_results:
  description:
    - One result list per statement, in execution order, as split by
      pyexasol.
    - In check mode, this is always empty because the script is not
      executed.
  returned: always
  type: list
  elements: list
executed_queries:
  description:
    - The statements pyexasol executed, in execution order.
    - In check mode, pyexasol does not split the script, so this contains
      the whole supplied script as a single entry instead of the real
      per-statement breakdown that execution produces.
    - This result is not redacted. Do not include secrets in O(script).
  returned: always
  type: list
  elements: str
  sample:
    - SELECT 1 AS A
rowcount:
  description:
    - Selected or affected row count for each executed statement.
    - Empty in check mode.
  returned: always
  type: list
  elements: int
  sample:
    - 1
execution_time_ms:
  description:
    - pyexasol-reported execution time for each executed statement, in
      milliseconds.
    - Empty in check mode.
  returned: always
  type: list
  elements: float
  sample:
    - 12.3
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.exasol.exasol.plugins.module_utils import (
    common_runtime_import,
)

common_runtime_import.make_source_runtime_importable_for_ansible_sanity(__file__)

from exasol.ansible_modules import exasol_script as exasol_script_utils


def main() -> None:
    """Run the Ansible module."""
    module = AnsibleModule(
        argument_spec=exasol_script_utils.module_argument_spec(),
        supports_check_mode=True,
    )

    params = module.params

    try:
        check_mode_result = (
            exasol_script_utils.check_mode_result(params["script"])
            if module.check_mode
            else None
        )
        if check_mode_result is not None:
            module.exit_json(**check_mode_result)
        result = exasol_script_utils.run_script(params)
    except ValueError as error:
        module.fail_json(msg=exasol_script_utils.sanitize_error_message(error, params))
    except Exception as error:  # noqa: BLE001 - Ansible modules report all failures.
        module.fail_json(
            msg=exasol_script_utils.normalized_exasol_error_message(
                error,
                params=params,
                operation="Exasol script execution",
            )
        )

    module.exit_json(**result)


if __name__ == "__main__":
    main()
