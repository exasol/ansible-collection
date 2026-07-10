---
orphan: true
---

# GH-38 Support Exact Exasol Identifiers In User And Role Modules

## Goal

Allow `exasol_user` and `exasol_role` to target exact Exasol identifier values, including names that require delimited-identifier syntax, without forcing uppercase normalization.

## Scope

In scope:

* update traced requirements and design for exact user and role identifier handling
* preserve exact identifier values in runtime validation, metadata probes, SQL generation, and module results
* extend unit and acceptance tests to cover mixed-case and special-character identifiers
* update module documentation and unreleased changelog entries

Out of scope:

* broadening exact-identifier handling to schema or object parameters outside `exasol_user` and `exasol_role`
* changing Exasol's own case-insensitive comparison behavior for users and roles

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Building Block View](../design/building_block_view.md)
* [Runtime View](../design/runtime_view.md)
* [Quality Requirements](../design/quality_requirements.md)

## Strategy

Keep conservative regular-identifier validation for schema and object paths, but switch user and role handling to an exact-identifier parser and quoter that accepts raw values and delimited SQL identifier syntax.

## Task List

### Requirements And Design

- [x] Add traced requirement coverage for exact user and role identifier preservation
- [x] Add design coverage for shared exact-identifier handling in the runtime

### Implementation

- [x] Implement exact identifier parsing and quoting for user and role names
- [x] Preserve exact identifier values in `exasol_user` and `exasol_role` results and generated SQL

### Verification

- [x] Run `poetry run nox -s requirements:trace`
- [x] Run targeted unit tests for shared, user, and role runtime behavior
- [x] Run targeted acceptance tests for exact user and role identifiers when backend access is available

### Update user documentation

- [x] Update module documentation and unreleased changelog notes
