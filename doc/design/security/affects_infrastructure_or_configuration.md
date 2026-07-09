# Affects Infrastructure or Configuration

Yes.

The change affects connection configuration, secret provisioning, CI or release automation, and the operational guidance for running the modules.

## Main Threats

### Plaintext Credentials Leak Through Inventory Or CI
`thrt~plaintext-credentials-leak-through-inventory-or-ci~1`

Operators or automation could place credentials in plaintext inventory, CI configuration, or other unsafe inputs that later leak through logs or artifact metadata.

Status: draft

Needs: dsn

### Overly Broad Network Reach Exposes Exasol Endpoints
`thrt~overly-broad-network-reach-exposes-exasol-endpoints~1`

Automation environments with unnecessary network reach could expose Exasol administration endpoints to more systems or operators than intended.

Status: draft

Needs: dsn

### Missing Guidance Weakens TLS Or Secret Handling
`thrt~missing-guidance-weakens-tls-or-secret-handling~1`

Insecure defaults or incomplete operator guidance could normalize unsafe TLS trust configuration or weak secret-handling practices.

Status: draft

Needs: dsn

### Stale Credentials Remain Usable After Rotation Or Revocation
`thrt~stale-credentials-remain-usable-after-rotation-or-revocation~1`

If automation caches credentials or rotation and revocation workflows are unclear, replaced or revoked secrets could remain usable longer than intended or fail unpredictably during operational handover.

Status: draft

Needs: dsn

### Compromised Publishing Paths Ship Untrusted Artifacts
`thrt~compromised-publishing-paths-ship-untrusted-artifacts~1`

Misconfigured or compromised Galaxy publishing paths could release untrusted artifacts or disclose publishing credentials.

Status: draft

Needs: dsn

## Required Controls

* keep Vault-based or equivalent secret management as the documented baseline
* document required network reachability and approved endpoints only
* avoid introducing new persistent secret stores, background services, or cluster-control paths
* verify release and test automation do not print secrets
* protect namespace ownership and release-publishing credentials

## Mitigations

### Document Vault-Backed Secret Handling
`dsn~document-vault-backed-secret-handling~1`

Document Vault-backed secret handling as the normal operator workflow.

Status: draft

Covers:
- `thrt~plaintext-credentials-leak-through-inventory-or-ci~1`
- `thrt~missing-guidance-weakens-tls-or-secret-handling~1`

Needs: uman

### Keep Secret Rotation And Revocation Outside The Collection
`dsn~keep-secret-rotation-and-revocation-outside-the-collection~1`

Keep secret rotation and revocation outside the collection through external secret management and Exasol account administration. The collection must not retain credentials across tasks, and operator guidance must assume that rotated or revoked credentials are supplied afresh on the next run.

Status: draft

Covers:
- `thrt~stale-credentials-remain-usable-after-rotation-or-revocation~1`
- `thrt~missing-guidance-weakens-tls-or-secret-handling~1`

Needs: impl, uman

### Avoid Extra Control-Plane Services
`dsn~avoid-extra-control-plane-services~1`

Keep the collection as a direct client of Exasol. Do not add brokers, agents, background reconcilers, or long-lived helper services that cache credentials, queue privileged actions, or create another place where authorization and secret handling can drift from the database.

Status: draft

Covers:
- `thrt~overly-broad-network-reach-exposes-exasol-endpoints~1`

Needs: impl

### Treat CI Redaction And Publishing-Credential Protection As Release Gates
`dsn~treat-ci-redaction-and-publishing-credential-protection-as-release-gates~1`

Do not ship a release if CI logs can expose secrets or if Galaxy publishing credentials are not adequately protected. Secret-safe logs and protected release credentials are mandatory conditions for publishing, not best-effort hygiene.

Status: draft

Covers:
- `thrt~plaintext-credentials-leak-through-inventory-or-ci~1`
- `thrt~compromised-publishing-paths-ship-untrusted-artifacts~1`

Needs: impl

## Applicable Questions

* In which network zone will the connector run?
* Does the connector require direct access to sensitive systems or databases?
* Are firewall rules restricted to only necessary endpoints and ports?
* How are secrets rotated and revoked?
