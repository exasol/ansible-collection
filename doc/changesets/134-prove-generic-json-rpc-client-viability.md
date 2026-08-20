---
orphan: true
---

# GH-134 Prove Generic JSON-RPC Client Viability

## Goal

Prove that Python can perform a generic JSON-RPC exchange independently of
confd, so later confd evidence can distinguish a protocol/client failure from
a confd-specific integration problem.

## Scope

In scope:

* add a controlled localhost JSON-RPC smoke test using Python's standard
  library
* verify request serialization, response parsing, request-ID correlation,
  protocol-error handling, timeout handling, and secret-safe error reporting
* document the selected client approach and its dependency/security review

Out of scope:

* contacting confd or selecting a confd access path
* production JSON-RPC or Ansible module code
* changes to `integration-test-docker-environment`, runtime dependencies, or
  public module parameters

## Design References

* [System Requirements](../system_requirements.md)
* [Confd Access-Spike Evaluation](../design/confd_access_spike_evaluation.md)
* [Architecture Constraints](../design/constraints.md)
* [Quality Requirements](../design/quality_requirements.md)
* [External Interfaces and APIs](../design/security/impacts_external_interfaces_apis.md)
* [Sensitive Data Handling](../design/security/introduces_or_modifies_sensitive_data_handling_security_relevant_processing_or_data_access_behavior.md)

## Strategy

Use a loopback-only `http.server` fixture and `urllib.request` from the Python
standard library. The test-local helper is intentionally not a reusable confd
client or API framework. It supplies evidence for generic JSON-RPC viability
without adding a package dependency or reaching a confd deployment.

## Task List

- [x] Confirm the current working branch carries the GH-134 spike work.

### Requirements And Design

- [x] Confirm that GH-134 adds no user-visible behavior and needs no system
  requirement or acceptance scenario.
- [x] Record the standard-library client choice, its security properties, and
  the limits of the resulting evidence.
- [x] Add a design item requiring reproducible generic JSON-RPC smoke-test
  evidence.
- [x] Record the passing generic JSON-RPC viability result and its explicit
  confd-specific limits.
- [x] Document why the generic protocol proof uses a controlled unit test and
  reserves confd integration testing for the later interface comparison.

### Implementation

- [x] Add a controlled loopback JSON-RPC smoke-test fixture and client helper.
- [x] Verify successful request/response serialization and request-ID
  correlation.
- [x] Verify protocol-error and timeout handling redact supplied secret values.

### Verification

- [x] Run the targeted JSON-RPC smoke tests.
- [x] Run `poetry run nox -s requirements:trace`.

### Update User Documentation

- [x] Confirm that this internal spike evidence does not change the end-user
  collection interface or require user-guide updates.

## Version And Changelog Update

- [x] Confirm that this test-only spike does not require a version or
  changelog entry.
