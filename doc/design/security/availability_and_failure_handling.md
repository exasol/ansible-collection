### Availability and Failure Handling

The administration surface is operational tooling, not a high-availability control plane. Availability therefore depends on Exasol reachability, valid credentials, and predictable failure behavior.

#### Main Threats

##### Invalid Inputs Or SQL Paths Cause Unsafe Failures
`thrt~invalid-inputs-or-sql-paths-cause-unsafe-failures~1`

Authentication, validation, or SQL-construction failures could trigger unsafe execution paths or make operational failures harder to recover from.

Status: draft

Needs: dsn

##### Partial Failures Leave State Unsafe For Repeated Runs
`thrt~partial-failures-leave-state-unsafe-for-repeated-runs~1`

Operational failures during multi-step changes could leave state in a condition that makes subsequent runs unsafe or misleading.

Status: draft

Needs: dsn

##### Autonomous Retries Repeat Privileged Actions
`thrt~autonomous-retries-repeat-privileged-actions~1`

Background retries or local retry loops could reissue privileged SQL and amplify unintended changes.

Status: draft

Needs: dsn

##### Check Mode Diverges From Real Execution
`thrt~check-mode-diverges-from-real-execution~1`

Check mode that does not follow the same planning logic as normal execution could mislead operators about pending security-relevant effects.

Status: draft

Needs: dsn

#### Required Controls

* fail fast on authentication, validation, and SQL-construction errors
* keep repeated runs safe after partial operational failures
* avoid background retries or local reconciliation loops that could amplify privilege changes
* keep check mode and idempotent planning available so operators can assess impact before applying changes

#### Mitigations

##### Validate Inputs Before Risky SQL Paths
`dsn~validate-inputs-before-risky-sql-paths~1`

Reject invalid or conflicting module inputs before building or executing administrative SQL. This includes malformed identifiers, unsupported option combinations, and inputs that would make the target operation ambiguous or unsafe.

Status: draft

Covers:
- `thrt~unsafe-inputs-enable-sql-injection-or-statement-abuse~1`
- `thrt~ambiguous-inputs-trigger-unintended-sql-effects~1`
- `thrt~invalid-inputs-or-sql-paths-cause-unsafe-failures~1`

Needs: impl, utest

##### Keep Check-Mode Planning Deterministic And Side-Effect Free
`dsn~keep-check-mode-planning-deterministic-and-side-effect-free~1`

Make check mode run the same planning logic as normal execution, but stop before any state-changing SQL is sent. Given the same requested state and database metadata, check mode should produce the same decision and reporting without creating side effects.

Status: draft

Covers:
- `scn~repeated-runs-do-not-add-unrequested-authorization-changes~1`
- `thrt~partial-authorization-failures-leave-inconsistent-state~1`
- `thrt~replayed-execution-repeats-destructive-effects~1`
- `thrt~partial-failures-leave-state-unsafe-for-repeated-runs~1`
- `thrt~check-mode-diverges-from-real-execution~1`

Needs: impl, utest

##### Avoid Autonomous Retry Of Privileged Actions
`dsn~avoid-autonomous-retry-of-privileged-actions~1`

Avoid autonomous retry behavior that could repeat privileged actions.

Status: draft

Covers:
- `thrt~replayed-execution-repeats-destructive-effects~1`
- `thrt~autonomous-retries-repeat-privileged-actions~1`

Needs: impl
