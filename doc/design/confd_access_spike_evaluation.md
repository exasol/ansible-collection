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

## JSON-RPC Validation

A controlled generic JSON-RPC smoke test is a prerequisite, not the confd
validation itself. It must show that the proposed Python client can:

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

### Generic JSON-RPC Client Viability
`dsn~generic-json-rpc-client-viability~1`

The generic prerequisite is implemented as a reproducible, loopback-only unit
test. It uses Python's `urllib.request` standard-library client and a
controlled local HTTP fixture to serialize an HTTP JSON-RPC request, parse its
response, correlate its request ID, and safely handle JSON-RPC errors and
timeouts. The test helper is not a confd adapter or a public Python API.

The standard-library approach adds no runtime dependency, credential store, or
network access beyond the local fixture. It is appropriate for this protocol
viability check because request serialization, timeout behavior, and error
handling remain explicit. It does not decide the eventual confd client library,
confd authentication model, TLS configuration, or endpoint topology.

The smoke test passes for a JSON-RPC round trip, response-ID correlation,
protocol-error redaction, and timeout redaction. JSON-RPC is therefore viable
as a Python integration mechanism in general. This result is limited to the
generic protocol path and does not establish confd compatibility.

Status: draft

Covers:
- `constr~generic-json-rpc-evidence-isolated-from-confd~1`

Needs: utest

#### Test-Level Rationale

This evidence is a unit test because its purpose is to isolate Python-side
JSON-RPC behavior from confd, credentials, network topology, and deployment
configuration. Although it is a unit test, it performs a real HTTP/JSON-RPC
round trip to the controlled loopback fixture rather than mocking the HTTP
client.

An integration test at this stage would need a confd endpoint, credentials,
and a representative Ansible execution environment. A failure could then be
caused by confd compatibility, authentication, authorization, reachability,
or port exposure instead of the Python client. Those concerns are deliberate
inputs to the later confd comparison: that work must run an authenticated,
read-only JSON-RPC operation against confd and compare it with
`confd_client` over SSH.

After the generic smoke test passes, the JSON-RPC candidate must be evaluated
against confd itself. From a representative Ansible execution environment, the
spike must prove that the client can:

* authenticate to the confd JSON-RPC endpoint with the intended
  least-privileged identity;
* send the agreed read-only confd request and receive the expected response;
* correlate the confd response to its request ID when the protocol provides
  one; and
* distinguish authentication or authorization denial, endpoint reachability,
  and protocol failure without exposing secrets in the recorded evidence.

Only this authenticated confd exchange establishes that JSON-RPC is a viable
confd access path. If the environment or credentials needed for it are not
available, the spike must record that as an unresolved decision blocker rather
than infer success from the generic smoke test.

## Ansible Execution Topology And Port Exposure

The spike must establish where operators are expected to run Ansible: for
example, on a host within the Exasol network, on a separate automation host,
or through a controlled bastion. This is an open input to the decision, not an
assumption that confd ports are exposed to every Ansible control node.

For each supported execution topology, the spike must record whether the confd
JSON-RPC endpoint is deliberately reachable from the Ansible host and, if so,
how that reachability is secured. A JSON-RPC recommendation is acceptable only
when the required route is compatible with least exposure and the supported
operator topology. If the route would require broadly exposing a confd port to
machines that should not reach it, that is evidence against the JSON-RPC
candidate or requires a separately reviewed deployment change.

## Test-Environment Reachability Assessment

The JSON-RPC assessment must inspect the current
`integration-test-docker-environment` configuration and record:

* whether confd listens on a JSON-RPC endpoint in the test image;
* whether the endpoint is reachable from a Python process representing the
  intended Ansible execution topology;
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

A new Python API project is not a default outcome, but potential ConfD
automation use cases beyond this collection are a required input to the
decision. The spike must identify the plausible consumers of a ConfD Python
API and determine whether they need the same stable abstraction as Ansible.

A dedicated project may be proposed when that assessment establishes a shared
public API contract, identified ownership and release responsibility, and a
justified dependency and packaging model. Otherwise the selected adapter
remains within the Ansible-facing runtime package, while the decision record
captures the potential reuse cases for later review.

## Required Spike Output

The final decision record must contain:

1. the recommendation and rejected alternative;
2. the sanitized evidence for the generic JSON-RPC smoke test, the
   authenticated JSON-RPC-to-confd exchange, and both confd candidates,
   including any unavailable candidate;
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
