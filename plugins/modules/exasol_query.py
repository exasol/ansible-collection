#!/usr/bin/python
# Copyright: (c) 2026, Exasol AG <opensource@exasol.com>
# MIT License (see LICENSE or https://opensource.org/license/mit)

DOCUMENTATION = r"""
---
module: exasol_query
short_description: Execute SQL statements against Exasol
description:
  - Executes one or more SQL statements against an Exasol database using
    pyexasol.
  - A list of statements runs on one connection in the supplied order.
  - SELECT-only invocations report C(changed=false). DDL and DML statements
    report C(changed=true).
  - SQL supplied through O(query) is returned in C(executed_queries). Do not
    include passwords, tokens, or other secrets in query text.
attributes:
  check_mode:
    description: Executes read-only SQL and predicts writable SQL without modifying Exasol.
    support: full
version_added: "0.1.0"
author:
  - Exasol AG (@exasol)
extends_documentation_fragment:
  - exasol.exasol.connection
options:
  query:
    description:
      - SQL statement or ordered list of SQL statements to execute.
      - Do not include passwords, tokens, or other secrets because this value
        is returned in C(executed_queries).
    type: raw
    required: true
  positional_args:
    description:
      - Positional values bound to C(?) placeholders in O(query).
      - The values are escaped with pyexasol's SQL formatter.
    type: list
    elements: raw
  named_args:
    description:
      - Named values bound to C(:name) placeholders in O(query).
      - The values are escaped with pyexasol's SQL formatter.
    type: dict
requirements:
  - exasol-ansible-modules
"""

EXAMPLES = r"""
---
- name: Read Exasol version metadata
  exasol.exasol.exasol_query:
    login_host: db.example.com
    login_user: "{{ vault_exasol_user }}"
    login_password: "{{ vault_exasol_password }}"
    login_schema: reporting
    query: >-
      SELECT PARAM_VALUE
      FROM EXA_METADATA
      WHERE PARAM_NAME = 'databaseProductVersion'

- name: Run a batch on one Exasol connection
  exasol.exasol.exasol_query:
    login_host: db.example.com
    login_user: "{{ vault_exasol_user }}"
    login_password: "{{ vault_exasol_password }}"
    query:
      - CREATE SCHEMA IF NOT EXISTS demo
      - CREATE OR REPLACE TABLE demo.t (id DECIMAL(18,0))
      - INSERT INTO demo.t VALUES (1)

- name: Bind positional and named values
  exasol.exasol.exasol_query:
    login_host: db.example.com
    login_user: "{{ vault_exasol_user }}"
    login_password: "{{ vault_exasol_password }}"
    query: SELECT ? AS A, :name AS B
    positional_args:
      - 42
    named_args:
      name: example
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
    - One result list per executed statement, in execution order.
    - Statements without a result set contribute an empty list.
  returned: always
  type: list
  elements: list
executed_queries:
  description:
    - SQL statements supplied to the module, in execution order.
    - This result is not redacted. Do not include secrets in O(query).
  returned: always
  type: list
  elements: str
  sample:
    - SELECT 1 AS A
rowcount:
  description:
    - Selected or affected row count for each statement.
  returned: always
  type: list
  elements: int
  sample:
    - 1
execution_time_ms:
  description:
    - pyexasol-reported execution time for each statement, in milliseconds.
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

from exasol.ansible_modules import exasol_query as exasol_query_utils


def main() -> None:
    """Run the Ansible module."""
    module = AnsibleModule(
        argument_spec=exasol_query_utils.module_argument_spec(),
        supports_check_mode=True,
    )

    params = module.params

    try:
        queries = exasol_query_utils.normalize_query_list(params["query"])
        check_mode_result = (
            exasol_query_utils.check_mode_result(queries) if module.check_mode else None
        )
        if check_mode_result is not None:
            module.exit_json(**check_mode_result)
        result = exasol_query_utils.run_query(params)
    except ValueError as error:
        module.fail_json(msg=exasol_query_utils.sanitize_error_message(error, params))
    except Exception as error:  # noqa: BLE001 - Ansible modules report all failures.
        module.fail_json(
            msg=exasol_query_utils.normalized_exasol_error_message(
                error,
                params=params,
                operation="Exasol query",
            )
        )

    module.exit_json(**result)


if __name__ == "__main__":
    main()
