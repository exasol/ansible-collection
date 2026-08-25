# ConfD Access Spike Experiment Log

This log records the GH-135 runtime observations. It is evidence for a later
architecture decision and does not select a production ConfD access path.

## Question

Can the collection evaluate ConfD through JSON-RPC or through
`confd_client` over SSH in a disposable Docker-DB fixture, and what test
environment changes are required?

## Observations

* The controlled generic JSON-RPC smoke tests pass. They confirm only that the
  Python test client can make a JSON-RPC request, correlate a response, and
  redact errors and timeouts.
* The Docker-DB EXAConf contains `XMLRPCPort = 443`; Docker does not forward
  `443/tcp` to the host. The `XMLRPCPort` name does not establish which RPC
  protocol `confd_client` uses internally. It cannot support a conclusion that
  ConfD JSON-RPC is absent.
* `confd_client db_list -j` completed once through an ITDE-generated root SSH
  key and returned the fixture database list. This is a manual observation of
  the root authorization boundary only; it does not prove a least-privilege
  identity or repeatable session behavior.
* The SSH-enabled ITDE fixture failed its bounded readiness phase on local
  Docker Desktop and in Ubuntu GitHub Actions. The CI run reported `193
  passed, 174 skipped, 96 warnings, 3 errors` after 560.35 seconds. The three
  ConfD tests skipped after the sanitized fixture-precondition error so GH-135
  could deliver its recorded limitation.

## Current Interpretation

The ConfD JSON-RPC candidate remains unverified. ConfD needs a reachable RPC
endpoint from the test client; the current Docker-DB port bindings do not
provide one. A dedicated ITDE change must expose the relevant ConfD RPC port
with local-only or Docker-network-only reachability and protected transport
before a JSON-RPC integration test can establish the protocol, authentication,
authorization, error, and timeout behavior.

The existing `XMLRPCPort = 443` observation remains useful configuration
evidence. It does not substitute for a protocol-level request.

## Follow-ups

* ITDE [#673](https://github.com/exasol/integration-test-docker-environment/issues/673)
  must make `db_os_access=SSH` produce an SSH-ready Docker-DB fixture.
* Collection [#143](https://github.com/exasol/ansible-collection/issues/143)
  restores failure behavior and reruns the SSH evidence tests after #673.
* ITDE [#676](https://github.com/exasol/integration-test-docker-environment/issues/676)
  must expose the ConfD RPC port with a local security boundary before
  JSON-RPC evidence can run.

## Security Notes

The experiment used a disposable fixture, an owner-only generated SSH key,
bounded SSH connection and command timeouts, and a temporary known-hosts file.
The recorded results exclude generated keys, credentials, host addresses, and
ephemeral ports. Any port-exposure follow-up must avoid all-interface shared
development defaults and validate transport before exposing the RPC endpoint.
