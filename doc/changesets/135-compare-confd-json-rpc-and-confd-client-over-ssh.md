---
orphan: true
---

# GH-135 Ansible Confd: Compare Confd JSON-RPC And `confd_client` Over SSH

## Goal

Collect sanitized runtime evidence for the actual ConfD boundaries in the
Docker integration-test fixture and determine whether JSON-RPC requires an
ITDE port-exposure change.

## Scope

In scope:

* inspect the current ITDE source, Docker-DB image configuration, and runtime
  port mappings without committing any infrastructure change
* execute the agreed read-only `confd_client db_list -j` operation over the
  disposable SSH fixture
* execute the agreed read-only ConfD JSON-RPC operation through the private
  Docker-DB container IP without changing ITDE port mappings
* assess SSH keys, identity privilege, transport, timeout/session behavior,
  and secret-safe evidence handling

Out of scope:

* a public Ansible module, production ConfD client, dependency, or non-test
  environment change
* an ITDE port-mapping change or a new ConfD Python API project

## Design References

* [Temporary ConfD Access-Spike Trace Contract](../design/confd_access_spike_evaluation.md)
* [ConfD Access Spike Experiment Log](../experiments/confd_access_spike_log.md)
* [Quality Requirements](../design/quality_requirements.md)
* [System Requirements](../system_requirements.md)

## Strategy

Use one disposable local Docker-DB fixture and the existing, test-only generic
JSON-RPC smoke evidence. First use the private container-IP route for ConfD
JSON-RPC protocol and authentication evidence. Consider SSH tunnelling only
after ITDE #673 if that route cannot reach ConfD; defer host-port exposure until
the selected implementation needs it.

## Task List

- [x] Confirm the GH-135 feature branch.

### Requirements And Design

- [x] Confirm that this internal spike introduces no user-visible behavior or
  new acceptance scenario.
- [x] Record comparable sanitized JSON-RPC and SSH evidence in the separate
  ConfD access-spike experiment log.
- [x] Record the configured RPC-port boundary and defer ITDE
  [#676](https://github.com/exasol/integration-test-docker-environment/issues/676)
  until the selected implementation needs host-port exposure.
- [x] Record the unresolved decision and the approval-gated hand-off to GH-136.
- [x] Add traced design items for the disposable JSON-RPC boundary and
  read-only `confd_client` SSH evidence.

### Implementation

- [x] Run the smallest removable, read-only ITDE prototype.
- [x] Do not add production code, public module parameters, dependencies, or
  permanent test-environment configuration.
- [x] Add traced, removable ITDE-backed tests for the ConfD protocol/port
  boundary, authenticated container-IP JSON-RPC `db_list`, and root SSH
  `db_list`, including secret-safe authorization-denial checks.

### Verification

- [x] Run the targeted generic JSON-RPC smoke tests.
- [ ] Run the container-IP JSON-RPC evidence tests in Ubuntu CI and record the
  sanitized protocol and authentication result. The initial run failed before
  ConfD started because the on-prem fixture occupied ITDE's default BucketFS
  port `2580`; the spike fixture now uses temporary BucketFS host ports.
- [x] Run requirement tracing with `poetry run nox --no-venv -s
  requirements:trace` (the repository's plain command requires an unavailable
  `uv` executable in this environment).
- [x] Run the ITDE-backed ConfD tests in Ubuntu GitHub Actions: all three
  tests failed during SSH-enabled fixture setup after 560.35 seconds. The run
  produced reproducible ITDE readiness evidence and no SSH command evidence.
- [x] Temporarily skip SSH evidence tests only when ITDE reports that the
  SSH-enabled fixture is unavailable, pending ITDE
  [#673](https://github.com/exasol/integration-test-docker-environment/issues/673).
  After #673 is resolved, follow-up
  [#143](https://github.com/exasol/ansible-collection/issues/143) restores
  failure behavior and reruns the SSH evidence tests.

### Update User Documentation

- [x] Confirm that the internal evidence record changes no end-user interface
  and needs no user-guide update.

## Version And Changelog Update

- [x] Confirm that this test-only spike needs no version or changelog entry.
