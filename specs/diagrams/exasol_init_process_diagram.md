# Exasol Init — Process EventStorming Diagram

This diagram captures the Exasol environment-initialization process using
EventStorming notation: **Actors** (who triggers work), **Commands**
(orange, imperative — what an Actor asks for), **Aggregates** (yellow,
the consistency boundary that accepts a Command), **Events** (amber, past
tense — what happened), **Policies** (lilac, "whenever X then Y" reactions
that connect events to the next command), and **Read Models** (green, the
Exasol system-table projections used to decide *whether* a command has
anything to do).

It reflects the phase ordering implemented by the `exasol_init` module and
derived in `specs/glossary/exasol_init_glossary.md`:

1. **Role** and **User** creation are independent (no read-before-write
   dependency between them).
2. **Role Assignment** (`GRANT role TO user`) needs both a Role and a User to
   exist — a join point.
3. **Schema** creation is independent by default; it only depends on User
   creation when the schema's `owner` is being reassigned to an application
   user.
4. **Schema Privilege Grant** needs the Role/User *and* the Schema to
   exist — the second join point.
5. **Init Script** execution runs last, after the schema exists and the
   access-control model (both grant kinds) is in place.

```mermaid
%%{init: {"flowchart": {"curve": "basis"}} }%%
flowchart TD
    classDef actor fill:#fde68a,stroke:#92400e,color:#111827,font-weight:bold;
    classDef command fill:#60a5fa,stroke:#1d4ed8,color:#0b1220,font-weight:bold;
    classDef aggregate fill:#fde047,stroke:#a16207,color:#111827,font-weight:bold;
    classDef event fill:#fbbf24,stroke:#92400e,color:#111827;
    classDef policy fill:#c4b5fd,stroke:#5b21b6,color:#111827,font-style:italic;
    classDef readmodel fill:#86efac,stroke:#166534,color:#111827;

    Operator["Actor:\nAnsible Operator\n(Exasol DBA / automation)"]:::actor

    Operator -->|issues| CmdInit["Command:\nInitialize Exasol\nEnvironment"]:::command
    CmdInit --> AggRun[["Aggregate:\nInitialization Run\n(exasol_init)"]]:::aggregate

    %% Phase 0: parallel-safe Role / User creation
    AggRun -->|plans| CmdCreateRole["Command:\nCreate Role"]:::command
    AggRun -->|plans| CmdCreateUser["Command:\nCreate User"]:::command

    RM_Roles[("Read Model:\nEXA_ALL_ROLES")]:::readmodel -.probes.-> CmdCreateRole
    RM_Users[("Read Model:\nEXA_ALL_USERS")]:::readmodel -.probes.-> CmdCreateUser

    CmdCreateRole --> AggRole[["Aggregate:\nRole"]]:::aggregate
    CmdCreateUser --> AggUser[["Aggregate:\nUser"]]:::aggregate

    AggRole --> EvtRoleCreated["Event:\nRole Created"]:::event
    AggUser --> EvtUserCreated["Event:\nUser Created"]:::event
    AggUser --> EvtSessionGranted["Event:\nSession Granted"]:::event

    %% Join point 1: role assignment needs both Role and User
    EvtRoleCreated --> PolicyAssign{{"Policy:\nWhenever Role ∧ User exist,\nassign requested role grants"}}:::policy
    EvtUserCreated --> PolicyAssign
    PolicyAssign -->|triggers| CmdAssignRole["Command:\nAssign Role To User"]:::command
    RM_RoleGrants[("Read Model:\nEXA_DBA_ROLE_GRANTS")]:::readmodel -.probes.-> CmdAssignRole
    CmdAssignRole --> AggRoleAssignment[["Aggregate:\nRole Assignment"]]:::aggregate
    AggRoleAssignment --> EvtRoleAssigned["Event:\nRole Assigned To User"]:::event

    %% Phase: Schema creation, independent unless owner reassignment requested
    AggRun -->|plans| CmdCreateSchema["Command:\nCreate Schema"]:::command
    RM_Schemas[("Read Model:\nEXA_ALL_SCHEMAS")]:::readmodel -.probes.-> CmdCreateSchema
    EvtUserCreated -. "only if schema.owner\nis reassigned" .-> CmdChangeOwner["Command:\nChange Schema Owner"]:::command
    CmdCreateSchema --> AggSchema[["Aggregate:\nSchema"]]:::aggregate
    CmdChangeOwner --> AggSchema
    AggSchema --> EvtSchemaCreated["Event:\nSchema Created"]:::event
    AggSchema --> EvtSchemaOwnerChanged["Event:\nSchema Owner Changed"]:::event

    %% Join point 2: schema privilege grants need grantee AND schema
    EvtRoleAssigned --> PolicyGrant{{"Policy:\nWhenever Role ∧ User ∧ Schema exist,\napply requested schema grants"}}:::policy
    EvtSchemaCreated --> PolicyGrant
    PolicyGrant -->|triggers| CmdGrantPriv["Command:\nGrant Schema Privilege"]:::command
    RM_ObjPrivs[("Read Model:\nEXA_DBA_OBJ_PRIVS")]:::readmodel -.probes.-> CmdGrantPriv
    CmdGrantPriv --> AggSchemaGrant[["Aggregate:\nSchema Privilege Grant"]]:::aggregate
    AggSchemaGrant --> EvtSchemaGranted["Event:\nSchema Privilege Granted"]:::event

    %% Final phase: init scripts run last, after grants
    EvtSchemaGranted --> PolicyScripts{{"Policy:\nOnce grants are applied,\nrun init scripts"}}:::policy
    PolicyScripts -->|triggers| CmdRunScripts["Command:\nExecute Init Scripts"]:::command
    CmdRunScripts --> AggScript[["Aggregate:\nInit Script"]]:::aggregate
    AggScript --> EvtScriptsExecuted["Event:\nInit Scripts Executed"]:::event

    EvtScriptsExecuted --> EvtEnvReady["Event:\nExasol Environment\nInitialized"]:::event
```

## Reading the diagram

* **Parallel-safe swimlanes**: `Create Role` and `Create User` have no arrow
  between them — either can run first, or (conceptually) concurrently.
  `exasol_init` executes them sequentially over one connection (roles, then
  users) purely for deterministic output ordering, not because of a data
  dependency.
* **Conditional dependency**: the dashed edge from `User Created` to
  `Change Schema Owner` only fires when a `schemas[].owner` parameter is
  supplied and refers to a user managed in the same run.
* **Two join points (Policies)** are where the process genuinely cannot
  proceed until multiple aggregates exist: role assignment needs a Role and
  a User; schema-privilege grants need a Schema and a grantee (Role or
  User).
* **Init scripts are last** by policy, not just convention: they are
  trusted-operator SQL (same trust model as `exasol_query`) that assumes the
  access-control model is already in place.

See `specs/diagrams/exasol_init_domain_diagram.md` for the static aggregate
relationships, and `specs/glossary/exasol_init_glossary.md` for term
definitions.
