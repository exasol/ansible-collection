# Runtime View

This chapter describes relevant runtime interactions for the main use cases and extension points.

Terms use the definitions from [System Requirements](../system_requirements.md).

## User And Role Lifecycle Planning

### Exact Principal Identifier Lifecycle
`dsn~exact-principal-identifier-lifecycle~1`

**Given** an Ansible Operator supplies a user or role name as either a raw exact value or a delimited SQL identifier
**When** the module validates parameters, probes existing metadata, and plans `CREATE`, `ALTER`, or `DROP` statements
**Then** the runtime converts the input to one exact identifier value, uses that value for metadata lookups, and renders generated SQL with escaped delimited identifiers without uppercasing the name

Status: draft

Covers:
- `scn~exact-principal-identifiers-are-preserved~1`

Needs: impl, utest, itest

### Exasol Info Read-Only Metadata Retrieval
`dsn~exasol-info-read-only-metadata-retrieval~1`

**Given** an Ansible Operator requests information from `exasol_info`
**When** the module reads the required server metadata
**Then** it returns version, database name, and cluster size
**And** the result always reports `changed=false`

Status: draft

Covers:
- `scn~exasol-info-returns-version-and-cluster-size~1`

Needs: impl, utest, itest

## Open Issues

* The collection still uses conservative regular-identifier validation for schema and object names outside the user and role lifecycle modules.
