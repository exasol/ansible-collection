# Involves New Dependencies or Services

Yes.

The scope depends on `pyexasol` for SQL script execution support and on Ansible Galaxy packaging for a usable release artifact.

## Main Threats

### Dependency Changes Expand Supply-Chain Risk
`thrt~dependency-changes-expand-supply-chain-risk~1`

New or changed dependencies could introduce vulnerable or higher-risk code paths into authentication, transport, or SQL handling.

Status: draft

Needs: dsn

### Compromised Packages Enter The Install Path
`thrt~compromised-packages-enter-the-install-path~1`

Substituted, malicious, or otherwise compromised packages could enter the installation path and undermine collection security.

Status: draft

Needs: dsn

### Runtime Package Version Drift Breaks Security Expectations
`thrt~runtime-package-version-drift-breaks-security-expectations~1`

Version drift between the collection and its required runtime packages could silently change security-relevant behavior.

Status: draft

Needs: dsn

### Release Artifacts Misinstall Runtime Dependencies
`thrt~release-artifacts-misinstall-runtime-dependencies~1`

Release artifacts could install successfully while omitting or mismatching runtime dependencies needed for secure behavior.

Status: draft

Needs: dsn

## Required Controls

* keep dependencies minimal and versioned consistently
* validate that collection installation pulls the required Python package automatically
* review upstream `pyexasol` changes that affect authentication, transport, or script execution behavior
* verify release artifacts resolve dependencies from the intended source only

## Mitigations

### Limit The Runtime Dependency Set
`dsn~limit-the-runtime-dependency-set~1`

Keep the runtime dependency set limited to `pyexasol` and `sqlglot`.

Status: draft

Covers:
- `thrt~dependency-changes-expand-supply-chain-risk~1`

Needs: impl

### Verify Packaging Installs Runtime Dependencies
`dsn~verify-packaging-installs-runtime-dependencies~1`

Verify packaging and installation through collection build and documentation checks.

Status: draft

Covers:
- `thrt~runtime-package-version-drift-breaks-security-expectations~1`
- `thrt~release-artifacts-misinstall-runtime-dependencies~1`

Needs: impl

### Review Dependency Changes During Release Verification
`dsn~review-dependency-changes-during-release-verification~1`

Review dependency changes as part of release verification for security-sensitive paths.

Status: draft

Covers:
- `thrt~dependency-changes-expand-supply-chain-risk~1`
- `thrt~compromised-packages-enter-the-install-path~1`

Needs: impl

## Applicable Questions

* Does the integration affect compliance scope?
* What permissions are required by the connector in the third-party system?
