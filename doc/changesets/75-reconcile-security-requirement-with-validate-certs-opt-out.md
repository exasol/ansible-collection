---
orphan: true
---

# GH-75 Reconcile Security Requirement With `validate_certs` Opt-Out

## Goal

Make the transport-security requirements, module API, and runtime behavior
consistent by preserving the documented fingerprint-pinning path while
rejecting fully untrusted TLS connections.

## Scope

In scope:

* update the traced transport requirement and design items to describe the
  supported trust modes accurately
* reject `validate_certs: false` unless `certificate_fingerprint` is provided
* align shared connection documentation, defaults, and tests with the stricter
  runtime contract

Out of scope:

* changing pyexasol transport behavior beyond the collection's shared parameter
  validation and mapping
* adding new backend acceptance coverage beyond the touched runtime tests

## Design References

* [System Requirements](../system_requirements.md)
* [Design](../design_index.md)
* [Crosscutting Concepts](../design/crosscutting_concepts.md)
* [Security Considerations](../design/security_considerations.md)
* [Quality Requirements](../design/quality_requirements.md)

## Strategy

Keep TLS encryption mandatory, keep CA validation enabled by default, and allow
CA-validation opt-out only when the operator pins the expected certificate
fingerprint explicitly.

## Task List

### Requirements And Design

- [x] Reconcile the transport requirement and scenarios with the supported trust
  modes
- [x] Update the design and security mitigations to reject fully untrusted TLS
  sessions while preserving fingerprint pinning

### Implementation

- [x] Reject `validate_certs: false` unless `certificate_fingerprint` is set
- [x] Align shared module documentation and setup defaults with the secure
  runtime contract

### Verification

- [x] Run targeted unit tests for shared Exasol connection handling
- [x] Run `poetry run nox -s requirements:trace`
- [x] Run `poetry run nox -s collection:doc`
- [x] Run `poetry run nox -s collection:sanity`
