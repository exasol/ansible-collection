---
orphan: true
---

# GH-79 Implement The Exasol Script Module

## Goal

Execute controller-side, multi-statement SQL scripts against Exasol from
Ansible playbooks and the reusable Python runtime package.

## Scope

In scope:

* execute an ordered SQL script as one pyexasol `execute_sql_script` call
* support Exasol script bodies (for example `CREATE ... SCRIPT`) that embed
  semicolons and are terminated by a standalone `/` line
* report `changed` based on whether the executed statements were read-only
* stop at the first failing statement and surface a sanitized error message
* support check mode by classifying the whole script as read-only or not,
  without adding a second SQL-script parser

Out of scope:

* a second, in-collection SQL-script parser or splitter; all script-splitting
  behavior comes from upstream `pyexasol`
* bound query parameters for scripts; pyexasol does not support them
* per-statement check-mode prediction; check mode reports the whole script as
  one predicted unit when it is not read-only

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Runtime View](../design/runtime_view.md)
* [Quality Requirements](../design/quality_requirements.md)

## Strategy

Mirror `exasol_query`'s thin-module-over-reusable-runtime shape. Reuse the
shared connection, error-sanitization, and result-shape helpers in
`common_query` and `exasol_query.is_read_only_query` rather than
reimplementing them. Execution defers entirely to
`ExaConnection.execute_sql_script`, added upstream in pyexasol 2.3.0
(exasol/pyexasol#348), which was the blocker for this issue.

## Task List

### Requirements And Design

- [x] Confirm pyexasol 2.3.0 ships `execute_sql_script` and record its
      contract (splits on statement-terminating semicolons, honors Exasol
      script bodies terminated by a standalone `/` line, stops at the first
      failing statement, does not support query parameters)
- [x] Decide the check-mode contract given pyexasol only splits a script as
      part of executing it: classify the whole script via the existing
      sqlglot-based read-only heuristic instead of a private pyexasol
      splitter import
- [x] Record the reused-field-name decision for the module's return shape
      (identical to `exasol_query`'s `query_result` / `query_all_results` /
      `executed_queries` / `rowcount` / `execution_time_ms`)

### Implementation

- [x] Require `pyexasol>=2.3.0` in `pyproject.toml`
- [x] Add `exasol.ansible_modules.exasol_script` runtime module
      (`module_argument_spec`, `execute_script`, `check_mode_result`,
      `run_script`), reusing `common_query` and
      `exasol_query.is_read_only_query`
- [x] Add `plugins/modules/exasol_script.py` Ansible module entry point
- [x] Register the module in the `connection` action group in
      `meta/runtime.yml`
- [x] Add the module to the sanity ignore list for the GPLv3-license check
- [x] Add unit tests for the runtime module
- [x] Add mocked ansible-test integration coverage
      (`tests/integration/targets/exasol_script`), extending the shared
      pyexasol mock base with `execute_sql_script` support
- [x] Add runtime-package and playbook acceptance scenarios and their
      matching Gherkin feature files, including the missing scenarios beyond
      the ticket's stated acceptance criteria (script-body-with-slash
      execution, read-only-without-check-mode, partial-failure side effects,
      write check-mode prediction, credential sanitization, and rejection of
      unsupported bound arguments)
- [x] Add backend acceptance coverage for two `CREATE SCRIPT` bodies in one
      script, each terminated by a standalone `/` line
- [x] Document the module in the user guide

### Verification

- [x] Run the scenario synchronization contract tests
- [x] Run the new unit tests
- [x] Run `ansible-test sanity` and `ansible-doc` for the new module
- [x] Run the mocked ansible-test integration target for `exasol_script` and
      confirm the shared mock-base change does not regress the other targets
- [x] Run formatting, linting, and typing checks
- [x] Run `poetry run nox -s requirements:trace`
