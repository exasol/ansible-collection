---
orphan: true
---

# GH-133 Define Confd Access-Spike Evaluation Contract

## Goal

Define a bounded, evidence-based contract for deciding whether a future
Ansible confd integration should use JSON-RPC or `confd_client` over SSH,
without selecting an interface or implementing a public module prematurely.

## Scope

In scope:

* document the comparison operation, evidence to collect, decision criteria,
  and security guardrails for the confd access spike
* define the generic JSON-RPC smoke-test boundary that must be satisfied before
  using JSON-RPC evidence for confd
* define how the spike determines whether
  `integration-test-docker-environment` needs an additional exposed port
* define the evidence required before proposing a dedicated Python API project

Out of scope:

* selecting JSON-RPC or SSH, or implementing either Ansible-facing interface
* c4 wrapper work, cluster lifecycle work, and unrelated collection changes
* a long-lived Python API project, a new secret store, or production release
  work
* permanent changes to `integration-test-docker-environment`

## Design References

* [System Requirements](../system_requirements.md)
* [Architecture Decisions](../design/architecture_decisions.md)
* [Security Considerations](../design/security_considerations.md)
* [External Interfaces and APIs](../design/security/impacts_external_interfaces_apis.md)
* [Infrastructure and Configuration](../design/security/affects_infrastructure_or_configuration.md)
* [Quality Requirements](../design/quality_requirements.md)

## Strategy

Keep the issue documentation-only. Establish comparable evidence and explicit
stop conditions first; later spike issues may run a minimal prototype only
when that evidence cannot settle the decision.

## Task List

- [x] Confirm work is on the GH-133 feature branch.

### Requirements And Design

- [x] Confirm that GH-133 creates no user-visible behavior and therefore needs
  no new system requirement or acceptance scenario.
- [x] Add the confd access-spike evaluation contract to the design
  documentation.
- [x] Define the two interfaces, a common read-only comparison operation, and
  the generic JSON-RPC smoke-test prerequisite.
- [x] Define evidence, decision criteria, prototype stop conditions, and
  follow-up ownership rules.
- [x] Define security and isolation requirements for credentials, transport,
  authorization, logging, and shared test infrastructure.

### Implementation

- [x] Do not add production code, dependencies, public Ansible parameters, or
  test-environment configuration in this contract issue.

### Verification

- [x] Run `poetry run nox -s requirements:trace`.

### Update User Documentation

- [x] Confirm that the internal spike contract does not change the end-user
  collection interface or require user-guide updates.

## Version And Changelog Update

- [x] Confirm that this documentation-only spike contract does not require a
  version or changelog entry.
