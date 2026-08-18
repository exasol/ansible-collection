# Confd Access-Spike Evaluation

This chapter defines the evidence contract for GH-133 and its follow-up spike
issues. It is not an interface decision and does not add a public Ansible
module, runtime dependency, or network endpoint.

## Decision To Be Made

The spike must recommend one bounded access path for future Ansible work:

1. a Python client talking to confd through JSON-RPC; or
2. a Python caller invoking `confd_client` through SSH.

The recommendation must also state whether JSON-RPC works with the selected
Python client in a generic protocol smoke test, whether the JSON-RPC path
needs a change to `integration-test-docker-environment` to expose a port, and
whether ownership warrants a dedicated Python API project.

The spike does not assume that either candidate works. A failed candidate is a
valid outcome when the failure is reproducible and its boundary is recorded.

## Comparison Contract

Both candidates must be assessed against the same smallest useful confd
operation. Before either confd-facing check runs, the follow-up issue must
name the operation, its expected read-only result, and the required confd
authorization. The operation must not create, modify, restart, or delete a
cluster resource.

The evidence record for each candidate must contain, with sensitive values
redacted:

* the client and confd versions, execution environment, and test fixture used;
* the request or command shape and the expected read-only result shape;
* authentication method, required identity, and minimum observed permission;
* endpoint reachability, including host-side port mapping when applicable;
* transport protection and trust configuration;
* successful result, authorization denial, connection failure, timeout, and
  protocol or command failure behavior;
* observed session setup, reuse, and teardown behavior when it affects the
  choice; and
* dependency, packaging, maintenance, and testability implications.

The comparison must distinguish an unavailable service, a blocked network
path, an authentication or authorization denial, and a protocol/client defect.
It must not report all of these as a generic integration failure.

## JSON-RPC Prerequisite

Before confd is used as JSON-RPC evidence, a controlled generic JSON-RPC smoke
test must show that the proposed Python client can:

* send a JSON-RPC request with a request ID and parse its successful response;
* correlate the response to that request ID;
* surface a JSON-RPC error response without exposing request credentials or
  endpoint-sensitive data; and
* fail predictably on a timeout or unavailable local endpoint.

The smoke endpoint is a controlled fixture, not confd. Passing it establishes
only that the Python protocol path is viable in general; it does not establish
confd compatibility, reachable deployment topology, or confd authorization.

If this prerequisite fails, the JSON-RPC candidate must not be treated as a
viable confd path until a focused follow-up explains and resolves the failure.

## Test-Environment Reachability Assessment

The JSON-RPC assessment must inspect the current
`integration-test-docker-environment` configuration and record:

* whether confd listens on a JSON-RPC endpoint in the test image;
* whether the endpoint is reachable from the Python test process with the
  current network topology;
* whether a host port mapping, Docker-network-only route, or no additional
  exposure is required; and
* the least-exposure configuration that permits the read-only test.

No permanent port mapping is part of this spike. If a mapping is needed for the
selected path or for decisive evidence, create a separately owned linked issue
in `integration-test-docker-environment`. That issue must restrict exposure to
the intended development/test boundary, document transport protection, and add
its own verification. A temporary local experiment must be reverted or kept
outside committed test-environment configuration.

## Security And Isolation Rules

The spike follows the collection's existing secret-safe and least-privilege
model:

* SSH keys, JSON-RPC credentials, tokens, endpoint URLs containing credentials,
  and test secrets must come from existing test configuration or environment
  variables; they must never be hard-coded or logged.
* The evaluated identity must have only the permissions needed for the agreed
  read-only operation. An authorization denial is evidence, not a reason to
  broaden permissions without recording the justification.
* SSH and JSON-RPC transport settings must be recorded with their trust model.
  An exposed JSON-RPC endpoint without secure-by-default handling cannot be
  recommended merely because it is convenient in local tests.
* Prototype runs are confined to local, disposable test infrastructure. They
  must not target non-test environments or introduce a secret store, persistent
  service, background worker, or cluster-control path.
* Captured errors and the final recommendation must preserve enough interface
  identity for accountability while redacting sensitive host, user, credential,
  and request data.

## Decision Criteria And Stop Conditions

The final comparison must rate each candidate against the following criteria:

| Criterion | Required finding |
| --- | --- |
| Functional fit | It can execute the agreed read-only confd operation or has a documented blocker. |
| Least privilege | The required identity and permissions are explicit and no broader than necessary. |
| Authentication and transport | Credential handling and secure-by-default transport are known and acceptable. |
| Test topology | Required reachability and any Docker-environment change are explicit. |
| Reliability | Timeouts, connection failures, protocol/command failures, and relevant session behavior are understood. |
| Maintainability | Dependencies, packaging, support ownership, and future test burden are proportionate. |
| Ansible fit | The boundary can remain a narrow runtime adapter behind a thin Ansible wrapper. |

Analysis alone is sufficient when authoritative interface documentation and
existing test-environment evidence answer every criterion without a material
assumption. A minimal prototype is required only when runtime evidence is
needed to distinguish candidates or resolve a material uncertainty. It must
end after the comparison operation and failure modes above are observed; it
must not grow into a reusable framework.

## Dedicated Python API Project Gate

A new Python API project is not a default outcome. It may be proposed only
when the selected JSON-RPC boundary has a demonstrated reuse case outside this
collection, a stable public API contract, identified ownership and release
responsibility, and a justified dependency/packaging model. Otherwise the
selected adapter remains within the Ansible-facing runtime package.

## Required Spike Output

The final decision record must contain:

1. the recommendation and rejected alternative;
2. the sanitized evidence for the generic JSON-RPC smoke test and both confd
   candidates, including any unavailable candidate;
3. the yes/no conclusion on JSON-RPC port exposure and the linked environment
   issue if a change is required;
4. the yes/no conclusion on a dedicated Python API project and its rationale;
5. whether a prototype was run or why analysis was enough; and
6. explicitly scoped follow-up issues, including their owning repository and
   required security and verification work.

## Explicit Non-Goals

The evaluation must not include c4 wrapper work, cluster lifecycle automation,
unrelated Ansible feature expansion, production hardening or release work, or
design of a general Python API framework before the confd boundary is proven.
