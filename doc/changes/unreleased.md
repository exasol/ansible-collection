# Unreleased

## Summary

* Added the Python toolbox compatible project setup.
* Added the Ansible collection skeleton, CI collection build and sanity
  tooling, and collection user/developer documentation.
* Added `exasol_query` module for executing SQL statements against Exasol
  directly from Ansible playbooks, enabling safe database automation and
  introspection.
* Added `exasol_user` module for user management support,
  allowing users to create, update, and delete database users in an
  idempotent and automation-safe way.

With **exasol_query**, users can execute arbitrary SQL statements with full control over:
- single or batched statement execution
- positional and named parameter binding
- read-only and write-capable execution modes
- safe check-mode simulation of write operations
- structured result handling (rows, row counts, timing)

With **exasol_user**, users can now fully manage Exasol database users in an idempotent way:
- create users with password or LDAP authentication
- update authentication method (e.g. switch from password to LDAP)
- rotate passwords safely
- drop users conditionally or forcefully
- ensure repeatable runs without unintended changes

## Features

* #3: Add Ansible collection skeleton
* #4: Add Ansible collection CI build and sanity checks
* #14: Add exasol_query for direct SQL execution from playbooks
* #22: Add exasol_query for direct SQL execution from playbooks - Part 2
* #32: Add exasol_user module

## Refactorings

* #2: Python Toolbox Compatible Project Bootstrap
* #5: Ansible Runner Test Harness
* #6: Exasol Backend Integration Smoke Test
* #12: Align collection identity, metadata, and standard repository skeleton
* #13: Implement shared Exasol module utilities and connection doc fragment
* #18: Use sqlglot for validate and other functions in plugin module_utils package