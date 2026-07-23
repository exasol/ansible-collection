# Use Case EventStorming Diagrams

EventStorming diagrams for every use case discovered from the Gherkin scenarios in
`specs/ansible_modules` and `specs/ansible_playbook`: the Ansible Operator issues a **command**,
an **aggregate** applies it, and the aggregate produces an **event** (or a **read model**, for the
two surfaces that never change Exasol state) or a **failure**.

## Overview

One representative branch per use case. Detailed per-use-case diagrams below expand every
command/event branch a use case's scenarios exercise.

```mermaid
flowchart LR
    operator(["Ansible Operator"])

    subgraph gather_server_info["gather-server-info (exasol_info)"]
        direction TB
        CMD_GatherInfo["GatherServerInfo<br/>(Command)"]:::command
        AGG_ServerInfo["SERVER_INFO<br/>(Read Model)"]:::aggregate
        EVT_InfoReported["ServerInfoReported<br/>(Read Model, no state change)"]:::readmodel
        CMD_GatherInfo --> AGG_ServerInfo --> EVT_InfoReported
    end

    subgraph execute_query_batch_ov["execute-query-batch (exasol_query)"]
        direction TB
        CMD_ExecuteQueryBatch["ExecuteQueryBatch<br/>(Command)"]:::command
        AGG_QueryExecution["QUERY_EXECUTION<br/>(Aggregate)"]:::aggregate
        EVT_QueryBatchExecuted["QueryBatchExecuted<br/>(Event)"]:::event
        CMD_ExecuteQueryBatch --> AGG_QueryExecution --> EVT_QueryBatchExecuted
    end

    subgraph execute_bound_query_ov["execute-bound-query (exasol_query)"]
        direction TB
        CMD_ExecuteBoundQuery["ExecuteBoundQuery<br/>(Command)"]:::command
        AGG_BoundQueryExecution["QUERY_EXECUTION<br/>(Aggregate)"]:::aggregate
        EVT_BoundQueryExecuted["BoundQueryExecuted<br/>(Event)"]:::event
        CMD_ExecuteBoundQuery --> AGG_BoundQueryExecution --> EVT_BoundQueryExecuted
    end

    subgraph execute_script_ov["execute-script (exasol_script)"]
        direction TB
        CMD_ExecuteScript["ExecuteScript<br/>(Command)"]:::command
        AGG_ScriptExecution["SCRIPT_EXECUTION<br/>(Aggregate)"]:::aggregate
        EVT_ScriptExecuted["ScriptExecuted /<br/>ScriptExecutionFailed<br/>(Event)"]:::event
        CMD_ExecuteScript --> AGG_ScriptExecution --> EVT_ScriptExecuted
    end

    subgraph reconcile_schema_ov["reconcile-schema (exasol_schema)"]
        direction TB
        CMD_CreateSchema["CreateSchema<br/>(Command)"]:::command
        AGG_Schema["SCHEMA<br/>(Aggregate)"]:::aggregate
        EVT_SchemaCreated["SchemaCreated<br/>(Event)"]:::event
        CMD_CreateSchema --> AGG_Schema --> EVT_SchemaCreated
    end

    subgraph reconcile_user_ov["reconcile-user (exasol_user)"]
        direction TB
        CMD_CreateUser["CreateUser<br/>(Command)"]:::command
        AGG_User["EXASOL_USER<br/>(Aggregate)"]:::aggregate
        EVT_UserCreated["UserCreated<br/>(Event)"]:::event
        CMD_CreateUser --> AGG_User --> EVT_UserCreated
    end

    subgraph reconcile_role_ov["reconcile-role (exasol_role)"]
        direction TB
        CMD_CreateRole["CreateRole<br/>(Command)"]:::command
        AGG_Role["EXASOL_ROLE<br/>(Aggregate)"]:::aggregate
        EVT_RoleCreated["RoleCreated<br/>(Event)"]:::event
        CMD_CreateRole --> AGG_Role --> EVT_RoleCreated
    end

    subgraph reconcile_grants_ov["reconcile-grants (exasol_grants)"]
        direction TB
        CMD_GrantPrivilege["GrantPrivilege<br/>(Command)"]:::command
        AGG_Grant["GRANT<br/>(Aggregate)"]:::aggregate
        EVT_PrivilegeGranted["PrivilegeGranted<br/>(Event)"]:::event
        CMD_GrantPrivilege --> AGG_Grant --> EVT_PrivilegeGranted
    end

    operator --> CMD_GatherInfo
    operator --> CMD_ExecuteQueryBatch
    operator --> CMD_ExecuteBoundQuery
    operator --> CMD_ExecuteScript
    operator --> CMD_CreateSchema
    operator --> CMD_CreateUser
    operator --> CMD_CreateRole
    operator --> CMD_GrantPrivilege

    classDef command fill:#ADD8E6,stroke:#333,color:#000
    classDef aggregate fill:#F0E68C,stroke:#333,color:#000
    classDef event fill:#FFA500,stroke:#333,color:#000
    classDef readmodel fill:#D3D3D3,stroke:#333,color:#000
```

GRANT records reference `EXASOL_USER` or `EXASOL_ROLE` as the granted principal, and a schema or
table as the granted object.

| Color | Meaning |
|---|---|
| Light blue | Command: what the Ansible Operator asked for |
| Khaki | Aggregate: the consistency boundary that applies the command |
| Orange | Event: the fact recorded once the command is applied |
| Light gray | Read model: a query result with no state change |
| Tomato (per-use-case diagrams below) | Failure: a rejected or failed command |

## gather-server-info (`exasol_info`)

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["SERVER_INFO<br/>(Aggregate, read-only)"]:::aggregate
    CMD_Gather["GatherServerInfo<br/>(Command)"]:::command
    RM_Reported["ServerInfoReported<br/>(Read Model)<br/>version, database_name,<br/>cluster_size; always changed=false"]:::readmodel

    operator --> CMD_Gather --> AGG --> RM_Reported

    classDef command fill:#ADD8E6,stroke:#333,color:#000
    classDef aggregate fill:#F0E68C,stroke:#333,color:#000
    classDef readmodel fill:#D3D3D3,stroke:#333,color:#000
```

This use case never mutates Exasol state, so it has no domain event: only a read model is
produced.

Source scenario: [exasol_info.feature](../../../specs/ansible_modules/exasol_info.feature).

## execute-query-batch (`exasol_query`)

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["QUERY_EXECUTION<br/>(Aggregate)"]:::aggregate

    CMD_Execute["ExecuteQueryBatch<br/>(Command)<br/>one statement or an<br/>ordered statement batch;<br/>no bound args"]:::command
    EVT_Executed["QueryBatchExecuted<br/>(Event)<br/>changed=true for any<br/>non-read-only statement"]:::event

    CMD_Predict["PredictQueryBatchExecution<br/>(Command, check mode)"]:::command
    EVT_Predicted["QueryBatchExecutionPredicted<br/>(Event)<br/>read-only statements still run;<br/>any write statement is skipped<br/>and the whole batch is predicted"]:::event

    CMD_BadAuth["ExecuteQuery<br/>(Command, bad credentials)"]:::command
    EVT_Failed["QueryBatchExecutionFailed<br/>(Event, Failure)<br/>sanitized authentication error,<br/>no secret values exposed"]:::failure

    operator --> CMD_Execute
    operator --> CMD_Predict
    operator --> CMD_BadAuth

    CMD_Execute --> AGG --> EVT_Executed
    CMD_Predict --> AGG --> EVT_Predicted
    CMD_BadAuth --> AGG --> EVT_Failed

    classDef command fill:#ADD8E6,stroke:#333,color:#000
    classDef aggregate fill:#F0E68C,stroke:#333,color:#000
    classDef event fill:#FFA500,stroke:#333,color:#000
    classDef failure fill:#FF6347,stroke:#333,color:#000
```

`ExecuteQueryBatch` accepts either one unbound statement or a list of statements. A list runs on
one connection in supplied order. `positional_args` and `named_args` are not accepted for this use
case because the module does not infer which statement should receive them.

Source scenarios: [exasol_query.feature](../../../specs/ansible_modules/exasol_query.feature),
[exasol_query.feature](../../../specs/ansible_playbook/exasol_query.feature) (`Execute statement batch on one connection` and
`Skip mixed read-write batch in check mode`).

## execute-bound-query (`exasol_query`)

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["QUERY_EXECUTION<br/>(Aggregate)"]:::aggregate

    CMD_Execute["ExecuteBoundQuery<br/>(Command)<br/>exactly one statement with<br/>positional and/or named args"]:::command
    EVT_Executed["BoundQueryExecuted<br/>(Event)<br/>changed=true for a<br/>non-read-only statement"]:::event

    CMD_Invalid["ExecuteBoundQuery<br/>(Command, invalid args)"]:::command
    EVT_Rejected["BoundQueryRejected<br/>(Event, Failure)<br/>a statement batch is supplied,<br/>or placeholders and arguments<br/>do not match"]:::failure

    operator --> CMD_Execute
    operator --> CMD_Invalid

    CMD_Execute --> AGG --> EVT_Executed
    CMD_Invalid --> AGG --> EVT_Rejected

    classDef command fill:#ADD8E6,stroke:#333,color:#000
    classDef aggregate fill:#F0E68C,stroke:#333,color:#000
    classDef event fill:#FFA500,stroke:#333,color:#000
    classDef failure fill:#FF6347,stroke:#333,color:#000
```

`ExecuteBoundQuery` accepts one `query` statement only. It uses `positional_args` for `?`
placeholders and `named_args` for `:name` placeholders. Supplying either argument collection with
a statement batch is rejected before execution.

Source scenarios: [exasol_query.feature](../../../specs/ansible_playbook/exasol_query.feature) (`Bind positional arguments`,
`Bind named arguments`, and `Reject bound arguments for statement batch`).

## execute-script (`exasol_script`)

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["SCRIPT_EXECUTION<br/>(Aggregate)"]:::aggregate

    CMD_Execute["ExecuteScript<br/>(Command)<br/>a semicolon-separated<br/>multi-statement script;<br/>CREATE ... SCRIPT bodies end<br/>with a standalone '/' line"]:::command
    EVT_Executed["ScriptExecuted<br/>(Event)<br/>changed=true for any<br/>non-read-only statement<br/>pyexasol split from the script"]:::event

    CMD_Predict["PredictScriptExecution<br/>(Command, check mode)"]:::command
    EVT_Predicted["ScriptExecutionPredicted<br/>(Event)<br/>read-only scripts still run;<br/>any other script is predicted<br/>as one opaque unit, not the<br/>real per-statement split"]:::event

    CMD_Failing["ExecuteScript<br/>(Command, failing statement)"]:::command
    EVT_Failed["ScriptExecutionFailed<br/>(Event, Failure)<br/>stops at the first failing<br/>statement; earlier statements'<br/>effects are not undone;<br/>sanitized error message"]:::failure

    operator --> CMD_Execute
    operator --> CMD_Predict
    operator --> CMD_Failing

    CMD_Execute --> AGG --> EVT_Executed
    CMD_Predict --> AGG --> EVT_Predicted
    CMD_Failing --> AGG --> EVT_Failed

    classDef command fill:#ADD8E6,stroke:#333,color:#000
    classDef aggregate fill:#F0E68C,stroke:#333,color:#000
    classDef event fill:#FFA500,stroke:#333,color:#000
    classDef failure fill:#FF6347,stroke:#333,color:#000
```

`ExecuteScript` never accepts `positional_args` or `named_args`: Ansible's own argument-spec
validation rejects them before the command reaches this aggregate, since pyexasol does not support
bound parameters for scripts.

Source scenarios: [exasol_script.feature](../../../specs/ansible_modules/exasol_script.feature),
[exasol_script.feature](../../../specs/ansible_playbook/exasol_script.feature).

## reconcile-schema (`exasol_schema`)

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["SCHEMA<br/>(Aggregate)"]:::aggregate

    CMD_Create["CreateSchema<br/>(Command)"]:::command
    EVT_Created["SchemaCreated<br/>(Event)"]:::event

    CMD_Drop["DropSchema<br/>(Command)"]:::command
    EVT_Dropped["SchemaDropped<br/>(Event)"]:::event

    CMD_Owner["ChangeSchemaOwner<br/>(Command)"]:::command
    EVT_Owner["SchemaOwnerChanged<br/>(Event)"]:::event

    CMD_Comment["SetSchemaComment<br/>(Command)"]:::command
    EVT_Comment["SchemaCommented<br/>(Event)"]:::event

    CMD_Rename["RenameSchema<br/>(Command)"]:::command
    EVT_Renamed["SchemaRenamed<br/>(Event)"]:::event

    CMD_Quota["SetSchemaRawSizeLimit<br/>(Command)"]:::command
    EVT_Quota["SchemaQuotaChanged<br/>(Event)"]:::event

    CMD_Predict["PredictSchemaChange<br/>(Command, check mode)<br/>covers every branch above"]:::command
    EVT_Predicted["SchemaChangePredicted<br/>(Event)<br/>same plan, no statement executed"]:::event

    CMD_DropUnsafe["DropSchema<br/>(Command, non-empty, no cascade)"]:::command
    EVT_DropRejected["SchemaDropRejected<br/>(Event, Failure)<br/>CASCADE required"]:::failure

    CMD_OwnerMissing["ChangeSchemaOwner<br/>(Command, owner missing)"]:::command
    EVT_OwnerFailed["SchemaOwnerAssignmentFailed<br/>(Event, Failure)<br/>CREATE SCHEMA already<br/>committed before the failure"]:::failure

    operator --> CMD_Create
    operator --> CMD_Drop
    operator --> CMD_Owner
    operator --> CMD_Comment
    operator --> CMD_Rename
    operator --> CMD_Quota
    operator --> CMD_Predict
    operator --> CMD_DropUnsafe
    operator --> CMD_OwnerMissing

    CMD_Create --> AGG --> EVT_Created
    CMD_Drop --> AGG --> EVT_Dropped
    CMD_Owner --> AGG --> EVT_Owner
    CMD_Comment --> AGG --> EVT_Comment
    CMD_Rename --> AGG --> EVT_Renamed
    CMD_Quota --> AGG --> EVT_Quota
    CMD_Predict --> AGG --> EVT_Predicted
    CMD_DropUnsafe --> AGG --> EVT_DropRejected
    CMD_OwnerMissing --> AGG --> EVT_OwnerFailed

    classDef command fill:#ADD8E6,stroke:#333,color:#000
    classDef aggregate fill:#F0E68C,stroke:#333,color:#000
    classDef event fill:#FFA500,stroke:#333,color:#000
    classDef failure fill:#FF6347,stroke:#333,color:#000
```

When the observed schema state already matches the requested state (existence, owner, comment,
rename, quota), the runtime issues no command and reports `changed=false`: an implicit "leave
unchanged" branch behind every command above.

Source scenario: [exasol_schema.feature](../../../specs/ansible_modules/exasol_schema.feature).

## reconcile-user (`exasol_user`)

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["EXASOL_USER<br/>(Aggregate)"]:::aggregate

    CMD_Create["CreateUser<br/>(Command, authentication_method=password)<br/>CREATE USER ... IDENTIFIED BY, plus<br/>GRANT CREATE SESSION when create_session=true"]:::command
    CMD_CreateLdap["CreateUser<br/>(Command, authentication_method=ldap)<br/>CREATE USER ... IDENTIFIED AT LDAP AS, plus<br/>GRANT CREATE SESSION when create_session=true"]:::command
    EVT_Created["UserCreated<br/>(Event)"]:::event

    CMD_UpdatePwd["UpdateUserPassword<br/>(Command, update_password=always)"]:::command
    EVT_PwdUpdated["UserPasswordUpdated<br/>(Event)"]:::event

    CMD_UpdateLdap["UpdateUserLdapDn<br/>(Command, authentication_method=ldap,<br/>ldap_dn differs from DISTINGUISHED_NAME)"]:::command
    EVT_LdapUpdated["UserLdapDnUpdated<br/>(Event)"]:::event

    CMD_Drop["DropUser<br/>(Command, cascade)"]:::command
    EVT_Dropped["UserDropped<br/>(Event)"]:::event

    CMD_Predict["PredictUserChange<br/>(Command, check mode)<br/>covers every branch above"]:::command
    EVT_Predicted["UserChangePredicted<br/>(Event)<br/>same plan, no statement executed"]:::event

    operator --> CMD_Create
    operator --> CMD_CreateLdap
    operator --> CMD_UpdatePwd
    operator --> CMD_UpdateLdap
    operator --> CMD_Drop
    operator --> CMD_Predict

    CMD_Create --> AGG
    CMD_CreateLdap --> AGG
    AGG --> EVT_Created
    CMD_UpdatePwd --> AGG --> EVT_PwdUpdated
    CMD_UpdateLdap --> AGG --> EVT_LdapUpdated
    CMD_Drop --> AGG --> EVT_Dropped
    CMD_Predict --> AGG --> EVT_Predicted

    classDef command fill:#ADD8E6,stroke:#333,color:#000
    classDef aggregate fill:#F0E68C,stroke:#333,color:#000
    classDef event fill:#FFA500,stroke:#333,color:#000
```

`update_password=on_create` only sets a password while creating the user. For an existing
password-authenticated user, the runtime issues no password-update command and reports
`changed=false`; Exasol does not expose password equality for comparison. `update_password` does
not apply to LDAP-authenticated users.

`authentication_method` defaults to `ldap` when `ldap_dn` is supplied, otherwise `password`.
`create_session` (default `true`) makes the `CREATE SESSION` grant on user creation optional rather
than implicit.

Source scenarios: [exasol_user.feature](../../../specs/ansible_modules/exasol_user.feature),
[exasol_user.feature](../../../specs/ansible_playbook/exasol_user.feature).

## reconcile-role (`exasol_role`)

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["EXASOL_ROLE<br/>(Aggregate)"]:::aggregate

    CMD_Create["CreateRole<br/>(Command)"]:::command
    EVT_Created["RoleCreated<br/>(Event)"]:::event

    CMD_Drop["DropRole<br/>(Command, cascade)"]:::command
    EVT_Dropped["RoleDropped<br/>(Event)"]:::event

    CMD_Predict["PredictRoleChange<br/>(Command, check mode)<br/>covers every branch above"]:::command
    EVT_Predicted["RoleChangePredicted<br/>(Event)<br/>same plan, no statement executed"]:::event

    operator --> CMD_Create
    operator --> CMD_Drop
    operator --> CMD_Predict

    CMD_Create --> AGG --> EVT_Created
    CMD_Drop --> AGG --> EVT_Dropped
    CMD_Predict --> AGG --> EVT_Predicted

    classDef command fill:#ADD8E6,stroke:#333,color:#000
    classDef aggregate fill:#F0E68C,stroke:#333,color:#000
    classDef event fill:#FFA500,stroke:#333,color:#000
```

When the role already exists (for `CreateRole`) or is already absent (for `DropRole`), the runtime
issues no command and reports `changed=false`.

Source scenario: [exasol_role.feature](../../../specs/ansible_modules/exasol_role.feature).

## reconcile-grants (`exasol_grants`)

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["GRANT<br/>(Aggregate)"]:::aggregate

    CMD_Grant["GrantPrivilege<br/>(Command)<br/>system_privileges or<br/>object_privileges, state=present"]:::command
    EVT_Granted["PrivilegeGranted<br/>(Event)"]:::event

    CMD_Revoke["RevokePrivilege<br/>(Command, state=absent)"]:::command
    EVT_Revoked["PrivilegeRevoked<br/>(Event)"]:::event

    CMD_Predict["PredictGrantChange<br/>(Command, check mode)<br/>covers both branches above"]:::command
    EVT_Predicted["GrantChangePredicted<br/>(Event)<br/>same plan, no statement executed"]:::event

    CMD_Ambiguous["GrantPrivilege<br/>(Command, user and role<br/>both supplied)"]:::command
    EVT_Rejected["GrantRequestRejected<br/>(Event, Failure)<br/>principal must be exactly<br/>one of user or role"]:::failure

    operator --> CMD_Grant
    operator --> CMD_Revoke
    operator --> CMD_Predict
    operator --> CMD_Ambiguous

    CMD_Grant --> AGG --> EVT_Granted
    CMD_Revoke --> AGG --> EVT_Revoked
    CMD_Predict --> AGG --> EVT_Predicted
    CMD_Ambiguous --> AGG --> EVT_Rejected

    classDef command fill:#ADD8E6,stroke:#333,color:#000
    classDef aggregate fill:#F0E68C,stroke:#333,color:#000
    classDef event fill:#FFA500,stroke:#333,color:#000
    classDef failure fill:#FF6347,stroke:#333,color:#000
```

`GRANT` is keyed by (principal, principal_type, object, privilege). When the observed privilege
state already matches the requested state, the runtime issues no command and reports
`changed=false`.

A single `GrantPrivilege`/`RevokePrivilege` command reconciles a batch of such tuples at once: one
per `system_privileges` entry, and one per privilege in each `object_privileges[]` entry. Each
`object_privileges[]` entry names its own schema, an optional object, and an optional object_type
(`function`, `script`, `table`, `view`, or `virtual_schema`) that disambiguates same-named objects.

Source scenarios: [exasol_grants.feature](../../../specs/ansible_playbook/exasol_grants.feature).
