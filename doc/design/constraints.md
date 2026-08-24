# Architecture Constraints

This chapter documents technical and organizational constraints that shape the architecture.

## Technical Constraints

* `<runtime, platform, framework, language, data, compatibility, or dependency constraint>`

### Generic JSON-RPC Evidence Is Isolated From Confd
`constr~generic-json-rpc-evidence-isolated-from-confd~1`

The generic JSON-RPC viability check must use a controlled local stub server.
It must not contact confd. It must not use confd credentials. It must not
require `integration-test-docker-environment` configuration. Confd
compatibility, authentication, and network-topology evidence belong to the
later interface comparison.

Rationale:

This keeps a Python protocol/client failure distinguishable from a confd or
deployment failure.

Status: draft

Needs: dsn

### Confd Spike Evidence Uses Disposable Test Infrastructure
`constr~confd-spike-evidence-is-disposable~1`

Confd access-spike evidence must run only against a disposable ITDE Docker-DB
fixture. The fixture must use temporary collection-owned output, SSH-key, and
known-host paths, clean up its container, volume, and network, and never use a
non-test deployment.

Rationale:

The spike evaluates a privileged administration boundary. Isolating the test
fixture prevents test credentials or ConfD commands from reaching an operator
environment and makes the result reproducible in the integration pipeline.

Status: draft

Needs: dsn

### `<Technical Constraint Title>`
`constr~<technical-constraint-id>~1`

`<Intentional technical constraint and the evidence source that makes it intentional.>`

Rationale:

`<Why this constraint shapes the architecture.>`

Status: draft

Needs: dsn

## Organizational Constraints

* `<release, operations, compliance, team, repository, process, or support constraint>`

### `<Organizational Constraint Title>`
`constr~<organizational-constraint-id>~1`

`<Intentional organizational constraint and the evidence source that makes it intentional.>`

Rationale:

`<Why this constraint shapes architecture, release, operations, or support.>`

Status: draft

Needs: dsn

## Assumptions

* `<assumption inferred from code or documentation>`

## Open Issues

* `<constraint contradiction or unresolved assumption>`
