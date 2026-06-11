#!/usr/bin/python
# Copyright: (c) 2026, Exasol AG <opensource@exasol.com>
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)

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
version_added: "0.1.0"
author:
  - Exasol AG (@exasol)
extends_documentation_fragment:
  - exasol.exasol.exasol_query
options:
  query:
    description:
      - SQL statement or ordered list of SQL statements to execute.
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
  - pyexasol
"""

EXAMPLES = r"""
---
- name: Read Exasol version metadata
  exasol.exasol.exasol_query:
    login_host: db.example.com
    login_user: "{{ vault_exasol_user }}"
    login_password: "{{ vault_exasol_password }}"
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

from typing import Any

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible_collections.exasol.exasol.plugins.module_utils.exasol_query import (
        build_exasol_connect_kwargs,
        exasol_connection_argument_spec,
        execute_queries,
        is_read_only_query,
        normalize_query_list,
        normalized_exasol_error_message,
        sanitize_error_message,
    )
except ImportError:
    from plugins.module_utils.exasol_query import (
        build_exasol_connect_kwargs,
        exasol_connection_argument_spec,
        execute_queries,
        is_read_only_query,
        normalize_query_list,
        normalized_exasol_error_message,
        sanitize_error_message,
    )


def main() -> None:
    """Run the Ansible module."""
    argument_spec = {
        **exasol_connection_argument_spec(),
        "query": {"type": "raw", "required": True},
        "positional_args": {"type": "list", "elements": "raw"},
        "named_args": {"type": "dict"},
    }
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    params = module.params
    query = params["query"]

    try:
        queries = normalize_query_list(query)
        if module.check_mode and not all(is_read_only_query(item) for item in queries):
            module.exit_json(
                changed=True,
                query_result=[],
                query_all_results=[],
                executed_queries=queries,
                rowcount=[],
                execution_time_ms=[],
            )

        result = run_query(params)
    except ValueError as error:
        module.fail_json(msg=sanitize_error_message(error, params))
    except Exception as error:  # noqa: BLE001 - Ansible modules report all failures.
        module.fail_json(
            msg=normalized_exasol_error_message(
                error,
                params=params,
                operation="Exasol query",
            )
        )

    module.exit_json(**result)


def run_query(params: dict[str, Any]) -> dict[str, Any]:
    """Connect to Exasol, execute query parameters, and close the connection."""
    try:
        import pyexasol
    except ImportError as error:
        raise RuntimeError(
            "pyexasol is required to use exasol_query. "
            "Install it in the Python environment that runs Ansible modules."
        ) from error

    connection = pyexasol.connect(**build_exasol_connect_kwargs(params))

    try:
        return execute_queries(
            connection,
            params["query"],
            positional_args=params.get("positional_args"),
            named_args=params.get("named_args"),
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
