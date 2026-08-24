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
* compare the result with the JSON-RPC candidate, recording a reproducible
  unavailable-path reason when no ConfD JSON-RPC endpoint exists
* assess SSH keys, identity privilege, transport, timeout/session behavior,
  and secret-safe evidence handling

Out of scope:

* a public Ansible module, production ConfD client, dependency, or non-test
  environment change
* an ITDE port-mapping change or a new ConfD Python API project

## Design References

* [Confd Access-Spike Evaluation](../design/confd_access_spike_evaluation.md)
* [Quality Requirements](../design/quality_requirements.md)
* [System Requirements](../system_requirements.md)

## Strategy

Use one disposable local Docker-DB fixture and the existing, test-only generic
JSON-RPC smoke evidence. Document unavailable JSON-RPC as an interface/config
boundary, not as a successful protocol test or a generic integration failure.

## Task List

- [x] Confirm the GH-135 feature branch.

### Requirements And Design

- [x] Confirm that this internal spike introduces no user-visible behavior or
  new acceptance scenario.
- [x] Record comparable sanitized JSON-RPC and SSH evidence in the ConfD
  access-spike design record.
- [x] Record the port-exposure conclusion and the conditions for a separately
  owned ITDE follow-up if XML-RPC is later evaluated.
- [x] Record the suggested outcome, GH-135 correction work, and the
  approval-gated hand-off to GH-136.
- [x] Add traced design items for the disposable JSON-RPC boundary and
  read-only `confd_client` SSH evidence.

### Implementation

- [x] Run the smallest removable, read-only ITDE prototype.
- [x] Do not add production code, public module parameters, dependencies, or
  permanent test-environment configuration.
- [x] Add traced, removable ITDE-backed tests for the ConfD protocol/port
  boundary and root SSH `db_list` operation, including an SSH authentication
  denial that does not disclose private-key material.

### Verification

- [x] Run the targeted generic JSON-RPC smoke tests.
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
