---
orphan: true
---

# GH-114 Make `login_schema` The Canonical Connection Parameter

## Goal

Make Exasol's schema-selection connection option clear and consistent without
breaking playbooks that use the historical `login_db` name.

## Scope

In scope:

* document `login_schema` as the canonical connection parameter
* retain `login_db` as a deprecated Ansible alias
* define deterministic handling when both names are supplied
* map the resolved schema value to pyexasol's `schema` argument
* update shared documentation, examples, tests, traceability, and changelog

Out of scope:

* removing `login_db`
* changing unrelated connection defaults or TLS behavior

## Design References

* [System Requirements](../system_requirements.md)
* [Crosscutting Concepts](../design/crosscutting_concepts.md)
* [Quality Requirements](../design/quality_requirements.md)

## Task List

### Requirements And Design

- [x] Specify the canonical schema parameter and compatibility behavior.
- [x] Define shared runtime mapping and precedence in the connection design.

### Implementation

- [x] Make `login_schema` canonical in the shared Ansible argument spec.
- [x] Keep `login_db` as a deprecated alias and preserve deterministic
  precedence when both names are supplied.
- [x] Map the resolved value to pyexasol's `schema` argument.

### Verification

- [x] Run focused unit tests for connection mapping.
- [x] Run `poetry run nox -s requirements:trace`.
- [x] Run `poetry run nox -s collection:doc`.
- [x] Run `poetry run nox -s collection:sanity`.

### User Documentation

- [x] Update shared module documentation, examples, user guide, and changelog.
