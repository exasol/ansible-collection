---
orphan: true
---

# GH-101 Use SQL_IDENTIFIER_COMPARISON Parameter for Schema Identifier Comparison Rule

## Goal

Make `exasol_schema` reconcile schema identifiers according to Exasol's
`SQL_IDENTIFIER_COMPARISON` parameter, and consolidate the associated backend
integration-test support.

## Scope

In scope:

* extract the reusable SQL-recording connection wrapper into
  `test/integration/common` and use it from backend integration tests
* read `SQL_IDENTIFIER_COMPARISON` from `SYS.EXA_PARAMETERS` when the server
  exposes it, falling back to Exasol's documented `CASE SENSITIVE` default
* compare schema names exactly for `CASE SENSITIVE` and without case for
  `IGNORE CASE`
* preserve case-insensitive owner comparison for user and role identifiers
* detect ambiguous case-insensitive schema metadata matches
* add specification and regression coverage for case-distinct schemas

Out of scope:

* changing `SQL_IDENTIFIER_COMPARISON`
* changing user or role identifier comparison behavior
* changing the privileges required to execute schema DDL

## Design References

* [System Requirements](../system_requirements.md)
* [Runtime View](../design/runtime_view.md)
* [Quality Requirements](../design/quality_requirements.md)

## Task List

### Requirements And Design

- [x] Confirm the SQL-recording helper extraction is an internal test-support
  refactor with no traced behavior change.
- [x] Specify schema lifecycle behavior that follows the database's
  identifier-comparison setting, with its documented default as fallback.
- [x] Define separate schema and principal identifier comparison rules.

### Implementation

- [x] Extract the recording connection wrapper into the integration-test common
  package and delegate the `exasol_info` integration test to it.
- [x] Add focused coverage for query recording, normalization, and delegation.
- [x] Read and validate `SQL_IDENTIFIER_COMPARISON` from
  `SYS.EXA_PARAMETERS` when available.
- [x] Use the identifier-comparison setting for schema lookup and rename
  planning.
- [x] Reject ambiguous case-insensitive schema matches.

### Verification

- [x] Run focused recording-helper tests.
- [x] Add unit regressions for both schema comparison modes and ambiguity.
- [x] Add backend integration coverage for default case-sensitive schemas.
- [x] Run backend integration coverage with configured Exasol credentials.
- [x] Run focused tests, formatting, linting, and OpenFastTrace tracing.
