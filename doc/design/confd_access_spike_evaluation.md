# Confd Access-Spike Evaluation

This chapter defines the evidence contract for GH-133 and its follow-up spike
issues. The chapter adds no interface decision, public Ansible module, runtime
dependency, or network endpoint.

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
* fail predictably when the controlled endpoint delays its response beyond the
  configured timeout, or when the local endpoint is unavailable.

The smoke endpoint is a controlled fixture, not confd. Passing it establishes
only that the Python protocol path is viable in general; it does not establish
confd compatibility, reachable deployment topology, or confd authorization.

If this prerequisite fails, the JSON-RPC candidate must not be treated as a
viable confd path until a focused follow-up explains and resolves the failure.

### Generic JSON-RPC Client Viability
`dsn~generic-json-rpc-client-viability~1`

The generic prerequisite is a loopback-only integration test using Python's
standard-library HTTP client and a controlled local fixture. It covers a
JSON-RPC round trip, response-ID correlation, and redaction of protocol errors
and timeouts.

Rationale:

The standard-library approach adds no runtime dependency,
credential store, or external network access, while keeping request
serialization, timeouts, and error handling explicit. It validates only the
generic Python JSON-RPC path; it does not establish confd compatibility or
decide the confd client library, authentication, TLS, or endpoint topology.

Status: draft

Covers:
- `constr~generic-json-rpc-evidence-isolated-from-confd~1`

Needs: itest

#### Test-Level Rationale

The test performs a real HTTP/JSON-RPC exchange
with a stub server. It isolates Python-side JSON-RPC behavior from confd while
the separate confd-level integration test evaluates compatibility,
authentication, authorization, reachability, and port exposure against confd.

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

### Docker-DB JSON-RPC Boundary Evidence
`dsn~confd-docker-json-rpc-boundary-evidence~1`

The ITDE-backed integration test must prove the configured ConfD protocol and
host-port boundary by inspecting the disposable Docker-DB EXAConf and Docker
port bindings. It must report an XML-RPC-only, unmapped ConfD endpoint as an
explicit JSON-RPC-unavailable result, not as a generic connection failure.

Status: draft

Covers:
- `constr~confd-spike-evidence-is-disposable~1`

Needs: itest

### Read-Only `confd_client` SSH Evidence
`dsn~confd-client-ssh-read-only-evidence~1`

The ITDE-backed integration test must use its temporary generated SSH key and
host-key file to execute `confd_client db_list -j` through the forwarded SSH
port. It must verify an owner-only key, parse the read-only JSON result, and
verify that a rejected SSH login does not expose private-key material.

Rationale:

The current ITDE fixture authenticates the generated key as root. This test
records that actual authorization boundary; it does not claim least-privilege
ConfD authorization until the fixture can provision a narrower SSH identity.

Status: draft

Covers:
- `constr~confd-spike-evidence-is-disposable~1`

Needs: itest

## Ansible Execution Topology And Port Exposure

The spike must establish where operators are expected to run Ansible: for
example, on a host within the Exasol network, on a separate automation host,
or through a controlled bastion. The decision retains this as an open input and
does not assume that confd ports are exposed to every Ansible control node.

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

## GH-135 Runtime Evidence: ConfD JSON-RPC And `confd_client` Over SSH

The following evidence was collected on 2026-08-24 from a disposable local
ITDE environment. It is deliberately limited to `db_list`, a ConfD operation
that returns database names and does not modify cluster state. Values that
would identify a local host, generated key, container, or ephemeral port are
represented by placeholders.

### Fixture And Reproduction Boundary

* Collection branch: `feature/135-ansible-confd-compare-confd-json-rpc-and-confd-client-over-ssh`.
* Generic JSON-RPC prerequisite: passed by the controlled loopback tests in
  `test/unit/test_json_rpc_smoke.py`. This proves only Python-side JSON-RPC
  request, response-ID, error-redaction, and timeout behavior.
* Test fixture: ITDE 6.4.1 with cached `exasol/docker-db:2026.1.0`; current
  ITDE source inspected at `e401fb0`.
* The disposable fixture was started with `--db-os-access SSH`. ITDE generated
  a per-user private key with mode `0600`, installed its public half in the
  container's root authorized-keys file, and removed the test container after
  the run. No collection code, public module interface, or committed ITDE
  configuration was changed.

### Automated CI Result

The Ubuntu GitHub Actions slow-integration job ran the three traced ConfD tests
with Python 3.12.14 and `--itde-db-version 8.29.13`. It did **not** produce
automated SSH evidence: each test failed during shared fixture setup with the
sanitized error `SSH-enabled ITDE fixture startup failed`. The full integration
run reported `193 passed, 174 skipped, 96 warnings, 3 errors` after 560.35
seconds.

This failure is a test-infrastructure blocker, not evidence that
`confd_client db_list -j` is denied or behaves incorrectly. The warnings came
from ITDE's `jsonpickle` compatibility code and Python 3.12's warning about
forking from a multi-threaded process. They may be relevant to the readiness
failure, but the current output does not establish causality. To deliver this
spike while ITDE resolves the blocker, the collection temporarily skips only
this `TaskRuntimeError` fixture-precondition outcome. The skip provides no
successful SSH evidence. ITDE
[#673](https://github.com/exasol/integration-test-docker-environment/issues/673)
must establish the readiness contract. Only after it is resolved, follow-up
[#143](https://github.com/exasol/ansible-collection/issues/143) restores
failure behavior so a future regression cannot be hidden behind a green CI
result.

### Overall Evidence Strategy

1. Generic smoke tests proved that the Python JSON-RPC client works against a
   controlled JSON-RPC server.
2. ITDE/Docker-DB configuration evidence shows that ConfD itself provides
   XML-RPC, not JSON-RPC, and that endpoint is not host-mapped. JSON-RPC is
   therefore rejected for ConfD. Report the unavailable protocol explicitly;
   do not report a generic connection failure.
3. SSH/`confd_client` is the remaining candidate. A manual read-only `db_list`
   probe succeeded, but its automated ITDE verification is temporarily skipped
   while ITDE [#673](https://github.com/exasol/integration-test-docker-environment/issues/673)
   is unresolved.

### Comparable Interface Evidence

| Evidence item | JSON-RPC to ConfD | `confd_client` over SSH |
| --- | --- | --- |
| Read-only operation | Unavailable: the Docker-DB EXAConf templates configure `XMLRPCPort = 443`; they contain no JSON-RPC listener or JSON-RPC request contract. | `ssh ... root@127.0.0.1 'confd_client db_list -j'` returned a JSON list containing the fixture database name. |
| Reachability and port mapping | ITDE's `Ports` and port-mapping code forward only database 8563, BucketFS 2580/2581, and SSH 22. The template `ExposedPorts` setting also omits 443. No JSON-RPC port is reachable or configured. | SSH 22 was forwarded to a random local host port for the disposable run. The host mapping used `0.0.0.0`, which is unsuitable as a secure shared-development default. |
| Authentication and authorization | Not testable: no endpoint exists in this image/configuration. The existing external-DB ITDE path uses HTTPS XML-RPC credentials, not JSON-RPC credentials. | Public-key SSH authentication as `root` succeeded using the ITDE-generated owner-only key. The ConfD `db_list` documentation permits `root`, `exaadm`, `exadbadm`, and `exausers`; this run demonstrated only `root`. |
| Transport and trust | Not applicable to the unavailable JSON-RPC path. A future XML-RPC evaluation would need HTTPS certificate validation; ITDE's external XML-RPC helper currently creates an unverified SSL context, which is unsuitable as a secure default. | SSH used an explicit private key, batch mode, a bounded connect timeout, and host-key pinning after first trust. The first connection used `accept-new` only for this disposable localhost fixture; a product path must provision and pin a known host key before connecting. |
| Session, timeout, retry, and errors | Generic smoke evidence shows a configured client timeout and redacted protocol errors, but provides no ConfD evidence. No ConfD JSON-RPC timeout or error semantics can be inferred. | One SSH session completed successfully. A subsequent connection timed out during banner exchange; one bounded retry was refused because the disposable fixture had been recreated/removed. The events record SSH transport/session failures. They provide no ConfD authorization or command-failure evidence. No automatic retry behavior was implemented or inferred. |
| Dependencies and operational fit | A client would need a real ConfD protocol and secure endpoint specification before it could be packaged or tested. The standard-library JSON-RPC smoke helper is test-only and cannot be reused as a ConfD client. | Requires the system SSH client (or a reviewed SSH library), a protected key, known-host handling, and a remote command timeout. It adds no collection runtime dependency in this spike. |

The command shape above intentionally uses `-j` so the read-only result can be
parsed without relying on human-oriented output. The saved evidence contains no
private key, password, endpoint credential, full host address, or generated
port.

### Security Assessment And Decision

The current fixture does **not** support JSON-RPC to ConfD. It supports a
separate HTTPS XML-RPC interface on internal port 443 and a local SSH route to
`confd_client`. Therefore JSON-RPC needs no ITDE port-exposure change: adding a
port would not make an absent protocol available. No linked ITDE issue is
created for JSON-RPC exposure.

The SSH route is functionally proven only for the root OS identity. A future
Ansible adapter requires a test fixture that provisions an SSH login/key for
the narrowest permitted ConfD
identity (expected candidate: `exausers`) and prove both allowed and denied
job behavior. A test attempt to switch to `exausers` did not reach
`confd_client`, because the disposable SSH fixture became unavailable; it must
not be reported as an authorization denial.

If a later issue evaluates ConfD **XML-RPC** instead, it must create a separate
linked ITDE issue before changing port exposure. That issue must add a
loopback- or Docker-network-scoped mapping for 443, require TLS certificate
validation and credentials from environment/test secrets, and verify that no
credential or endpoint-sensitive data appears in errors. It must not rely on
the existing all-interface (`0.0.0.0`) mapping for shared development.

No dedicated ConfD Python API project is justified: no stable remote protocol,
shared consumer contract, release owner, or least-privilege identity has been
established. A future, narrow SSH adapter should remain test-only until those
conditions are met.

### Suggested Outcome And Approval-Gated Next Steps

GH-135's suggested outcome is to reject JSON-RPC for the current Docker-DB
fixture: the generic client passed, but ConfD JSON-RPC is not configured or
reachable, so ConfD JSON-RPC is not a selectable candidate. The traced,
disposable ITDE tests define the required evidence for that boundary and the
read-only `confd_client` command. `confd_client` over SSH is the only candidate
with a successful manual ConfD operation, but it is a **leading candidate, not
an approved architecture decision**. Its evidence is insufficient for a
least-privilege production boundary because ITDE proves only root SSH access.

The integration tests skip when Docker or the local `ssh` executable is
unavailable, and temporarily also when ITDE raises `TaskRuntimeError` while
starting the SSH-enabled fixture. The temporary ITDE skip is limited to this
known blocker and does not verify the SSH assertions. CI must provide the
fixture and run those assertions successfully before the SSH evidence can be
treated as verified.

Before GH-136 can make an architecture decision, resolve ITDE
[#673: Add SSH-ready Docker-DB fixture support for GitHub
Actions](https://github.com/exasol/integration-test-docker-environment/issues/673):
make `db_os_access=SSH` reach an SSH-ready Docker-DB fixture on the Ubuntu
GitHub Actions configuration used by this collection, and add ITDE-level
coverage for that readiness contract. Its acceptance criteria must include
proving that readiness contract. After #673 is resolved, follow-up
[#143](https://github.com/exasol/ansible-collection/issues/143) removes the
temporary `TaskRuntimeError` skip, restores the sanitized test failure, and
reruns this collection's three ConfD tests. Do not create an Ansible SSH
runtime-adapter issue until #673 and #143 are resolved.

Only if the ITDE blocker cannot be resolved for a documented technical or
support reason, a separate, short-lived EC2 diagnostic may be considered. It
must exercise the same boundary: an EC2 host runs Docker, ITDE starts
Docker-DB with `db_os_access=SSH`, and the test uses ITDE's generated key and
forwarded SSH port to run `confd_client db_list -j` inside that Docker-DB
fixture. This diagnostic is not an acceptance-test replacement. It must use
disposable infrastructure and secret-safe credentials, and it must not be used
to bypass the ITDE blocker or approve an Ansible adapter.

After the GH-135 tests and requirement tracing are green, continue with GH-136
as an ADR-only approval issue. Its proposed recommendation is:

* reject JSON-RPC for the currently supported test/deployment boundary;
* select a narrow `confd_client`-over-SSH adapter only if the root-only
  authorization boundary is accepted by review; otherwise record "no adapter
  approved" and open an evidence-remediation issue instead of silently
  selecting root SSH;
* record that generic JSON-RPC passed but was not ConfD-compatible in this
  environment, that no JSON-RPC port exposure is required, and that a
  dedicated Python API project is not warranted; and
* create one collection implementation issue only after the ADR is approved:
  a thin Ansible wrapper over a narrow SSH runtime adapter, with no-log
  parameters, provided SSH key and known-host trust, explicit command/connect
  timeouts, sanitized failures, and backend integration coverage.

No additional `integration-test-docker-environment` issue is needed for JSON-RPC
port exposure under that outcome. If a future decision reopens XML-RPC or
another exposed remote protocol, first create a separate ITDE issue for
loopback- or Docker-network-only exposure, TLS validation, and its own
integration tests; do not add that infrastructure
work to the collection implementation issue.

## Explicit Non-Goals

The evaluation must not include c4 wrapper work, cluster lifecycle automation,
unrelated Ansible feature expansion, production hardening or release work, or
design of a general Python API framework before the confd boundary is proven.
