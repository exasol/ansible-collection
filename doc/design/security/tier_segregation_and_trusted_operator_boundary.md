# Tier Segregation and Trusted-Operator Boundary

These modules are designed for trusted operators running in controlled automation environments. In particular, `exasol_query` and `exasol_script` already execute operator-supplied SQL directly against Exasol, the latter as multi-statement scripts, extending the same trust model. The collection does not sandbox SQL semantics or downgrade the authority of the authenticated Exasol account.

## Main Threats

### Untrusted Tiers Reach Administrative Interfaces
`thrt~untrusted-tiers-reach-administrative-interfaces~1`

Running the collection from uncontrolled or overly broad automation tiers could expose Exasol administrative interfaces to untrusted environments.

Status: draft

Needs: dsn

### Shared Or Over-Privileged Accounts Cross Role Boundaries
`thrt~shared-or-over-privileged-accounts-cross-role-boundaries~1`

Using shared or overly privileged service accounts across automation roles could blur security boundaries and expand the impact of mistakes or misuse.

Status: draft

Needs: dsn

### Direct SQL Surfaces Are Mistaken For Sandboxed Interfaces
`thrt~direct-sql-surfaces-are-mistaken-for-sandboxed-interfaces~1`

Operators could incorrectly assume that direct SQL interfaces such as `exasol_query` or `exasol_script` constrain SQL semantics or reduce account authority.

Status: draft

Needs: dsn

### Declarative Modules Drift From The Trusted-Operator Security Model
`thrt~declarative-modules-drift-from-the-trusted-operator-security-model~1`

Future administrative modules could diverge from the established least-privilege, redaction, transport, and repeatable-planning model.

Status: draft

Needs: dsn

## Required Controls

* run the collection only from tiers that are allowed to reach Exasol administration endpoints
* use separate low-privilege connection accounts for distinct automation roles where possible
* treat `exasol_query`, `exasol_script`, `exasol_grants`, and `exasol_schema` as subject to the same least-privilege, redaction, and transport-protection rules
* require repeatable state-reconciliation planning only for modules that reconcile declarative authorization or schema state from observed metadata

## Mitigations

### Keep The Trust Boundary At The Authenticated Account And Operator Environment
`dsn~keep-the-trust-boundary-at-the-authenticated-account-and-operator-environment~1`

Treat the authenticated Exasol account and the automation environment running the playbook as the security boundary. The collection must not try to dilute, extend, or reinterpret that authority with its own privilege model.

Status: draft

Covers:
- `scn~operation-uses-authenticated-exasol-permissions~1`
- `thrt~over-privileged-service-accounts-expand-blast-radius~1`
- `thrt~untrusted-tiers-reach-administrative-interfaces~1`

Needs: impl

### Require Least-Privilege Service Accounts For Automation Tiers
`dsn~require-least-privilege-service-accounts-for-automation-tiers~1`

Use separate service accounts for separate automation roles and grant each account only the Exasol privileges required for its job. A playbook that manages users should not automatically inherit the rights needed for broader scripting or schema administration if it does not need them.

Comment:

In practice, this is enforced mainly through documentation, operational guidance, and account provisioning outside the collection: the collection can describe the expected privilege boundaries, but it cannot reliably downgrade or constrain an already over-privileged Exasol account supplied by the operator.

Status: draft

Covers:
- `thrt~over-privileged-service-accounts-expand-blast-radius~1`
- `thrt~overly-broad-network-reach-exposes-exasol-endpoints~1`
- `thrt~shared-or-over-privileged-accounts-cross-role-boundaries~1`

Needs: uman

### Apply The Security Model To Future Administrative Modules
`dsn~apply-the-security-model-to-future-administrative-modules~1`

Current `exasol_query`, `exasol_script`, `exasol_grants`, and `exasol_schema` modules, and any future administrative modules, must follow the same rules established here where they apply: no local privilege bypass, encrypted transport only, and least-privilege operation. Modules with structured outputs must keep those outputs secret-safe. Direct SQL surfaces such as `exasol_query` and `exasol_script` remain trusted-operator interfaces: they are explicitly exempt from both automatic redaction of arbitrary operator-supplied SQL text and the state-reconciliation rule. Modules that reconcile declarative authorization or schema state from observed metadata, such as `exasol_grants` or `exasol_schema`, must use repeatable planning based on observed database state.

Status: draft

Covers:
- `thrt~missing-guidance-weakens-tls-or-secret-handling~1`
- `thrt~direct-sql-surfaces-are-mistaken-for-sandboxed-interfaces~1`
- `thrt~declarative-modules-drift-from-the-trusted-operator-security-model~1`

Needs: impl
