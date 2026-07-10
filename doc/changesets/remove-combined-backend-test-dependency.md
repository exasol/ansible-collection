---
orphan: true
---

# Remove Combined Backend Test Dependency

## Goal

Keep pytest-driven integration tests focused on the on-prem Exasol backend and
remove the unused multi-backend dependency path from the test environment.

## Scope

In scope:

* replace the combined backend pytest plugin with direct ITDE setup for on-prem
  integration tests
* remove the backend selection option because integration tests only use ITDE
* remove transitive dependencies needed only by the replaced backend plugin from
  the lock file
* update developer documentation for the on-prem-only integration test setup

Out of scope:

* changing module behavior or user-facing collection features
* changing acceptance scenario requirements

## Design References

* [Quality Requirements](../design/quality_requirements.md)

## Task List

### Implementation

- [x] Add direct ITDE pytest fixtures
- [x] Replace the combined backend pytest plugin dependency with direct ITDE
- [x] Update developer documentation

### Verification

- [x] Run unit tests
- [x] Run integration test collection with ITDE options
- [x] Run `poetry run nox -s requirements:trace`
