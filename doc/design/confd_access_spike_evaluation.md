# Temporary ConfD Access-Spike Trace Contract

This temporary design contract traces the GH-135 evidence tests while the
ConfD access decision remains open. GH-136 must replace it with the approved
architecture decision and remove this contract when the temporary tests are
either retained under that decision or removed.

## Generic JSON-RPC Client Viability
`dsn~generic-json-rpc-client-viability~1`

A controlled loopback test verifies JSON-RPC request, response, error, and
timeout handling without contacting ConfD.

Status: draft

Covers:
- `constr~generic-json-rpc-evidence-isolated-from-confd~1`

Needs: itest

## Docker-DB ConfD RPC Port Boundary Evidence
`dsn~confd-docker-json-rpc-boundary-evidence~2`

The ITDE test records the configured ConfD RPC port and its Docker host-port
mapping. The JSON-RPC spike uses the container IP without a host-port mapping;
ITDE [#676](https://github.com/exasol/integration-test-docker-environment/issues/676)
remains deferred until a selected implementation needs host exposure.

Status: draft

Needs: itest

## Container-IP JSON-RPC Evidence
`dsn~confd-container-ip-json-rpc-evidence~1`

The ITDE test sends authenticated, read-only `db_list` JSON requests to the
ConfD container IP and verifies that an unknown bearer token is rejected
without disclosing the valid token. SSH tunnelling is a fallback after ITDE
[#673](https://github.com/exasol/integration-test-docker-environment/issues/673)
if the container-IP route cannot reach ConfD.

The test waits for ConfD's bounded post-start initialization before evaluating
the authenticated request or authorization denial.

Status: draft

Needs: itest

## Read-Only `confd_client` SSH Evidence
`dsn~confd-client-ssh-read-only-evidence~1`

The ITDE test runs `confd_client db_list -j` over SSH and checks temporary key
protection and secret-safe authentication-failure handling.

Status: draft

Needs: itest
