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

    subgraph gather_server_info["gather-server-info"]
        direction TB
        CMD_GatherInfo["GatherServerInfo\n(Command)"]:::command
        AGG_ServerInfo["SERVER_INFO\n(Read Model)"]:::aggregate
        EVT_InfoReported["ServerInfoReported\n(Read Model, no state change)"]:::readmodel
        CMD_GatherInfo --> AGG_ServerInfo --> EVT_InfoReported
    end

    subgraph execute_query_ov["execute-query"]
        direction TB
        CMD_ExecuteQuery["ExecuteQuery\n(Command)"]:::command
        AGG_QueryExecution["QUERY_EXECUTION\n(Aggregate)"]:::aggregate
        EVT_QueryExecuted["QueryExecuted\n(Event)"]:::event
        CMD_ExecuteQuery --> AGG_QueryExecution --> EVT_QueryExecuted
    end

    subgraph execute_script_ov["execute-script"]
        direction TB
        CMD_ExecuteScript["ExecuteScript\n(Command)"]:::command
        AGG_ScriptExecution["SCRIPT_EXECUTION\n(Aggregate)"]:::aggregate
        EVT_ScriptExecuted["ScriptExecuted /\nScriptExecutionFailed\n(Event)"]:::event
        CMD_ExecuteScript --> AGG_ScriptExecution --> EVT_ScriptExecuted
    end

    subgraph reconcile_schema_ov["reconcile-schema"]
        direction TB
        CMD_CreateSchema["CreateSchema\n(Command)"]:::command
        AGG_Schema["SCHEMA\n(Aggregate)"]:::aggregate
        EVT_SchemaCreated["SchemaCreated\n(Event)"]:::event
        CMD_CreateSchema --> AGG_Schema --> EVT_SchemaCreated
    end

    subgraph reconcile_user_ov["reconcile-user"]
        direction TB
        CMD_CreateUser["CreateUser\n(Command)"]:::command
        AGG_User["EXASOL_USER\n(Aggregate)"]:::aggregate
        EVT_UserCreated["UserCreated\n(Event)"]:::event
        CMD_CreateUser --> AGG_User --> EVT_UserCreated
    end

    subgraph reconcile_role_ov["reconcile-role"]
        direction TB
        CMD_CreateRole["CreateRole\n(Command)"]:::command
        AGG_Role["EXASOL_ROLE\n(Aggregate)"]:::aggregate
        EVT_RoleCreated["RoleCreated\n(Event)"]:::event
        CMD_CreateRole --> AGG_Role --> EVT_RoleCreated
    end

    subgraph reconcile_grants_ov["reconcile-grants"]
        direction TB
        CMD_GrantPrivilege["GrantPrivilege\n(Command)"]:::command
        AGG_Grant["GRANT\n(Aggregate)"]:::aggregate
        EVT_PrivilegeGranted["PrivilegeGranted\n(Event)"]:::event
        CMD_GrantPrivilege --> AGG_Grant --> EVT_PrivilegeGranted
    end

    operator --> CMD_GatherInfo
    operator --> CMD_ExecuteQuery
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

## gather-server-info

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["SERVER_INFO\n(Aggregate, read-only)"]:::aggregate
    CMD_Gather["GatherServerInfo\n(Command)"]:::command
    RM_Reported["ServerInfoReported\n(Read Model)\nversion, database_name,\ncluster_size; always changed=false"]:::readmodel

    operator --> CMD_Gather --> AGG --> RM_Reported

    classDef command fill:#ADD8E6,stroke:#333,color:#000
    classDef aggregate fill:#F0E68C,stroke:#333,color:#000
    classDef readmodel fill:#D3D3D3,stroke:#333,color:#000
```

This use case never mutates Exasol state, so it has no domain event: only a read model is
produced.

Source scenario: `specs/ansible_modules/exasol_info.feature`.

## execute-query

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["QUERY_EXECUTION\n(Aggregate)"]:::aggregate

    CMD_Execute["ExecuteQuery\n(Command)\none statement or an\nordered statement batch,\noptionally with bound args"]:::command
    EVT_Executed["QueryExecuted\n(Event)\nchanged=true for any\nnon-read-only statement"]:::event

    CMD_Predict["PredictQueryExecution\n(Command, check mode)"]:::command
    EVT_Predicted["QueryExecutionPredicted\n(Event)\nread-only statements still run;\nany write statement is skipped\nand the whole batch is predicted"]:::event

    CMD_Invalid["ExecuteQuery\n(Command, invalid bound args)"]:::command
    EVT_Rejected["QueryExecutionRejected\n(Event, Failure)\nbound args combined with a\nstatement batch, or a\npositional/named argument\ncount mismatch"]:::failure

    CMD_BadAuth["ExecuteQuery\n(Command, bad credentials)"]:::command
    EVT_Failed["QueryExecutionFailed\n(Event, Failure)\nsanitized authentication error,\nno secret values exposed"]:::failure

    operator --> CMD_Execute
    operator --> CMD_Predict
    operator --> CMD_Invalid
    operator --> CMD_BadAuth

    CMD_Execute --> AGG --> EVT_Executed
    CMD_Predict --> AGG --> EVT_Predicted
    CMD_Invalid --> AGG --> EVT_Rejected
    CMD_BadAuth --> AGG --> EVT_Failed

    classDef command fill:#ADD8E6,stroke:#333,color:#000
    classDef aggregate fill:#F0E68C,stroke:#333,color:#000
    classDef event fill:#FFA500,stroke:#333,color:#000
    classDef failure fill:#FF6347,stroke:#333,color:#000
```

Source scenarios: `specs/ansible_modules/exasol_query.feature`,
`specs/ansible_playbook/exasol_query.feature`.

## execute-script

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["SCRIPT_EXECUTION\n(Aggregate)"]:::aggregate

    CMD_Execute["ExecuteScript\n(Command)\na single multi-statement\nscript, including a script\nbody terminated by a\nstandalone '/' line"]:::command
    EVT_Executed["ScriptExecuted\n(Event)\nchanged=true for any\nnon-read-only statement\npyexasol split from the script"]:::event

    CMD_Predict["PredictScriptExecution\n(Command, check mode)"]:::command
    EVT_Predicted["ScriptExecutionPredicted\n(Event)\nread-only scripts still run;\nany other script is predicted\nas one opaque unit, not the\nreal per-statement split"]:::event

    CMD_Failing["ExecuteScript\n(Command, failing statement)"]:::command
    EVT_Failed["ScriptExecutionFailed\n(Event, Failure)\nstops at the first failing\nstatement; earlier statements'\neffects are not undone;\nsanitized error message"]:::failure

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

Source scenarios: `specs/ansible_modules/exasol_script.feature`,
`specs/ansible_playbook/exasol_script.feature`.

## reconcile-schema

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["SCHEMA\n(Aggregate)"]:::aggregate

    CMD_Create["CreateSchema\n(Command)"]:::command
    EVT_Created["SchemaCreated\n(Event)"]:::event

    CMD_Drop["DropSchema\n(Command)"]:::command
    EVT_Dropped["SchemaDropped\n(Event)"]:::event

    CMD_Owner["ChangeSchemaOwner\n(Command)"]:::command
    EVT_Owner["SchemaOwnerChanged\n(Event)"]:::event

    CMD_Comment["SetSchemaComment\n(Command)"]:::command
    EVT_Comment["SchemaCommented\n(Event)"]:::event

    CMD_Rename["RenameSchema\n(Command)"]:::command
    EVT_Renamed["SchemaRenamed\n(Event)"]:::event

    CMD_Quota["SetSchemaRawSizeLimit\n(Command)"]:::command
    EVT_Quota["SchemaQuotaChanged\n(Event)"]:::event

    CMD_Predict["PredictSchemaChange\n(Command, check mode)\ncovers every branch above"]:::command
    EVT_Predicted["SchemaChangePredicted\n(Event)\nsame plan, no statement executed"]:::event

    CMD_DropUnsafe["DropSchema\n(Command, non-empty, no cascade)"]:::command
    EVT_DropRejected["SchemaDropRejected\n(Event, Failure)\nCASCADE required"]:::failure

    CMD_OwnerMissing["ChangeSchemaOwner\n(Command, owner missing)"]:::command
    EVT_OwnerFailed["SchemaOwnerAssignmentFailed\n(Event, Failure)\nCREATE SCHEMA already\ncommitted before the failure"]:::failure

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

Source scenario: `specs/ansible_modules/exasol_schema.feature`.

## reconcile-user

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["EXASOL_USER\n(Aggregate)"]:::aggregate

    CMD_Create["CreateUser\n(Command, authentication_method=password)\nCREATE USER ... IDENTIFIED BY, plus\nGRANT CREATE SESSION when create_session=true"]:::command
    CMD_CreateLdap["CreateUser\n(Command, authentication_method=ldap)\nCREATE USER ... IDENTIFIED AT LDAP AS, plus\nGRANT CREATE SESSION when create_session=true"]:::command
    EVT_Created["UserCreated\n(Event)"]:::event

    CMD_UpdatePwd["UpdateUserPassword\n(Command, update_password=always)"]:::command
    EVT_PwdUpdated["UserPasswordUpdated\n(Event)"]:::event

    CMD_UpdateLdap["UpdateUserLdapDn\n(Command, authentication_method=ldap,\nldap_dn differs from DISTINGUISHED_NAME)"]:::command
    EVT_LdapUpdated["UserLdapDnUpdated\n(Event)"]:::event

    CMD_Drop["DropUser\n(Command, cascade)"]:::command
    EVT_Dropped["UserDropped\n(Event)"]:::event

    CMD_Predict["PredictUserChange\n(Command, check mode)\ncovers every branch above"]:::command
    EVT_Predicted["UserChangePredicted\n(Event)\nsame plan, no statement executed"]:::event

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

`update_password=on_create` only sets a password while creating the user; when the user already
exists with a matching password and `update_password=on_create`, the runtime issues no command and
reports `changed=false`. `update_password` does not apply to LDAP-authenticated users.

`authentication_method` defaults to `ldap` when `ldap_dn` is supplied, otherwise `password`.
`create_session` (default `true`) makes the `CREATE SESSION` grant on user creation optional rather
than implicit.

Source scenarios: `specs/ansible_modules/exasol_user.feature`,
`specs/ansible_playbook/exasol_user.feature`.

## reconcile-role

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["EXASOL_ROLE\n(Aggregate)"]:::aggregate

    CMD_Create["CreateRole\n(Command)"]:::command
    EVT_Created["RoleCreated\n(Event)"]:::event

    CMD_Drop["DropRole\n(Command, cascade)"]:::command
    EVT_Dropped["RoleDropped\n(Event)"]:::event

    CMD_Predict["PredictRoleChange\n(Command, check mode)\ncovers every branch above"]:::command
    EVT_Predicted["RoleChangePredicted\n(Event)\nsame plan, no statement executed"]:::event

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

Source scenario: `specs/ansible_modules/exasol_role.feature`.

## reconcile-grants

```mermaid
flowchart LR
    operator(["Ansible Operator"])
    AGG["GRANT\n(Aggregate)"]:::aggregate

    CMD_Grant["GrantPrivilege\n(Command)\nsystem_privileges or\nobject_privileges, state=present"]:::command
    EVT_Granted["PrivilegeGranted\n(Event)"]:::event

    CMD_Revoke["RevokePrivilege\n(Command, state=absent)"]:::command
    EVT_Revoked["PrivilegeRevoked\n(Event)"]:::event

    CMD_Predict["PredictGrantChange\n(Command, check mode)\ncovers both branches above"]:::command
    EVT_Predicted["GrantChangePredicted\n(Event)\nsame plan, no statement executed"]:::event

    CMD_Ambiguous["GrantPrivilege\n(Command, user and role\nboth supplied)"]:::command
    EVT_Rejected["GrantRequestRejected\n(Event, Failure)\nprincipal must be exactly\none of user or role"]:::failure

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

Source scenarios: `specs/ansible_playbook/exasol_grants.feature`.
