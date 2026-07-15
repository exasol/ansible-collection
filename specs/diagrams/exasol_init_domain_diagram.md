# Exasol Init — Domain Model Diagram

This is the static counterpart to
`specs/diagrams/exasol_init_process_diagram.md`: the Aggregates discovered by
EventStorming and how they relate, independent of execution order. Each
Aggregate is the consistency boundary for one Exasol object type; each
relationship is a real SQL dependency (a foreign concept in Exasol's own
catalog, not an artifact of this collection).

```mermaid
classDiagram
    direction LR

    class Role {
        <<Aggregate>>
        +String name
        +present|absent state
        +Boolean cascade
        CREATE ROLE
        DROP ROLE [CASCADE]
    }

    class User {
        <<Aggregate>>
        +String name
        +password|ldap authentication_method
        +present|absent state
        +on_create|always update_password
        +Boolean cascade
        CREATE USER
        ALTER USER
        DROP USER [CASCADE]
        GRANT CREATE SESSION
    }

    class Schema {
        <<Aggregate>>
        +String name
        +String owner
        +present|absent state
        +Boolean cascade
        CREATE SCHEMA
        ALTER SCHEMA CHANGE OWNER
        DROP SCHEMA [CASCADE]
    }

    class RoleAssignment {
        <<Aggregate>>
        +String role
        +String user
        +present|absent state
        GRANT role TO user
        REVOKE role FROM user
    }

    class SchemaPrivilegeGrant {
        <<Aggregate>>
        +String schema
        +String grantee
        +Privilege privilege
        +present|absent state
        GRANT privilege ON SCHEMA TO grantee
        REVOKE privilege ON SCHEMA FROM grantee
    }

    class InitScript {
        <<Aggregate>>
        +String sql
        trusted-operator SQL, executed unconditionally
    }

    class Privilege {
        <<ValueObject>>
        ALL | SELECT | INSERT | UPDATE | DELETE | ALTER | INDEX | REFERENCES | EXECUTE
    }

    class InitializationRun {
        <<ProcessManager>>
        exasol_init module: sequences every
        Aggregate below into one idempotent run
    }

    InitializationRun ..> Role : ensures
    InitializationRun ..> User : ensures
    InitializationRun ..> Schema : ensures
    InitializationRun ..> RoleAssignment : ensures
    InitializationRun ..> SchemaPrivilegeGrant : ensures
    InitializationRun ..> InitScript : executes

    Role "1" <-- "0..*" RoleAssignment : grants role
    User "1" <-- "0..*" RoleAssignment : to user
    Schema "0..1" <-- "0..1" User : optionally owned by
    Schema "1" <-- "0..*" SchemaPrivilegeGrant : grants on schema
    User "0..1" <-- "0..*" SchemaPrivilegeGrant : grantee (or Role)
    Role "0..1" <-- "0..*" SchemaPrivilegeGrant : grantee (or User)
    SchemaPrivilegeGrant --> Privilege : specifies
    Schema "1" <-- "0..*" InitScript : populates
```

## Notes on the relationships

* `RoleAssignment` is the resolved many-to-many relationship between `Role`
  and `User` — it exists only once both sides exist (see the process
  diagram's first Policy join).
* `Schema.owner` is an *optional* 0..1 relationship to `User`: a schema is
  always owned by *someone* in Exasol (defaulting to the connecting admin
  account), but `exasol_init` only manages that relationship when `owner` is
  explicitly supplied.
* `SchemaPrivilegeGrant.grantee` can reference either a `User` or a `Role` —
  Exasol's `GRANT ... TO` target accepts either principal type, so the
  aggregate models `grantee` as a discriminated reference rather than two
  separate aggregates.
* `InitScript` has no `state` (present/absent): scripts are trusted-operator
  SQL in the same sense as `exasol_query` — they are executed, not
  reconciled, and are therefore append-only within one initialization run.
* `InitializationRun` is a **process manager**, not a persisted Exasol
  object. It has no row in any Exasol system table; its only observable
  trace is the sequence of events it drives through the aggregates above.
