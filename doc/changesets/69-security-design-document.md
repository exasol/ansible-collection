---
orphan: true
---

# GH-69 Security design consistency fixes

## Goal

Align the requirements and design documents on TLS validation, administration-surface scope, and grant-management and schema-management behavior so the security design traces cleanly to the intended feature scope.

## Scope

In scope:

* extend the documented administration surface in `doc/system_requirements.md`
* make certificate validation non-optional in requirements and design
* cover grant-management repeated-run behavior in scenarios and design
* include `exasol_schema` in the documented administration surface
* add explicit security threat items and trace them to design mitigations
* align security-chapter applicable questions with the sections that answer them
* add threat and mitigation coverage for any remaining unanswered security questions
* record the documentation work in the per-issue changeset format used by this repository

Out of scope:

* production code changes
* new automated tests beyond trace verification

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Crosscutting Concepts](../design/crosscutting_concepts.md)
* [Security Considerations](../design/security_considerations.md)
* [Quality Requirements](../design/quality_requirements.md)

## Strategy

Repair the traced requirements first, then update the architecture chapters so the design language matches the stricter transport policy and broader administration scope.

## Task List

### Requirements And Design

- [x] Extend the documented requirements scope to cover the current and planned administration modules
- [x] Tighten the transport requirement and scenario to forbid relaxing certificate validation
- [x] Cover grant-management repeated-run behavior in acceptance scenarios and design items
- [x] Align the design chapters with the updated requirements scope and transport policy
- [x] Add `thrt` items to `doc/design/security_considerations.md` and trace mitigations to them
- [x] Move security questions to the sections that answer them when local coverage is not the best fit
- [x] Add `thrt` and `dsn` items for remaining unanswered security questions

### Verification

- [x] Run `poetry run nox -s requirements:trace`
- [ ] Run additional implementation or test suites if code changes are introduced
