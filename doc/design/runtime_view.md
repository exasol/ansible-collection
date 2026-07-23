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

### Exasol Script Execution Via Pyexasol
`dsn~exasol-script-execution-via-pyexasol~1`

**Given** an Ansible Operator supplies a multi-statement SQL script to `exasol_script`
**When** the runtime executes it through `ExaConnection.execute_sql_script`
**Then** pyexasol splits and executes the statements in order, including script bodies terminated by a standalone `/` line
**And** the runtime derives `changed` and `executed_queries` from the returned statements without a second, in-collection SQL-script parser
**And** check mode classifies the whole script as read-only or not, using the same heuristic as `exasol_query`, instead of executing it

Status: draft

Covers:
- `scn~exasol-script-executes-multi-statement-scripts~1`

Needs: impl, utest, itest

## Physical Schema Lifecycle Planning

### Intrinsic Schema Property Reconciliation
`dsn~intrinsic-schema-property-reconciliation~1`

**Given** an Ansible Operator requests physical schema state
**When** the schema runtime reads `EXA_SCHEMAS` and `EXA_ALL_OBJECT_SIZES`
**Then** it plans creation or rename before comment and raw-size changes, plans
`CHANGE OWNER` last, and omits statements for properties that already match
**And** omitted owner, comment, rename, and raw-size-limit options remain unmanaged
**And** check mode returns the same plan without executing it

Status: draft

Covers:
- `scn~schema-intrinsic-state-is-reconciled~1`
- `scn~schema-check-mode-reports-property-changes-without-writing~1`

Needs: impl, utest, itest

### Explicit Schema Drop Cascade
`dsn~explicit-schema-drop-cascade~1`

**Given** an Ansible Operator requests an existing schema to be absent
**When** the runtime plans the drop
**Then** it emits `DROP SCHEMA` by default and appends `CASCADE` only when the
operator explicitly enables the `cascade` option

Status: draft

Covers:
- `scn~non-cascading-drop-protects-non-empty-schema~1`

Needs: impl, utest, itest
