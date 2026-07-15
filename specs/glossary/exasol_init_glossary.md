# Exasol Init — Glossary (Ubiquitous Language)

This glossary defines the Ubiquitous Language for Exasol environment
initialization. Terms are derived from the existing
`specs/ansible_playbook/*.feature` and `specs/ansible_modules/*.feature`
scenarios for `exasol_user`, `exasol_role`, and `exasol_query`, extended with
the vocabulary discovered by EventStorming in
`specs/diagrams/exasol_init_process_diagram.md` and
`specs/diagrams/exasol_init_domain_diagram.md`. It is the shared vocabulary
for `specs/ansible_playbook/exasol_init_ansible_playbook.feature`,
`specs/ansible_modules/exasol_init_ansible_modules.feature`, and the
`exasol_init` runtime — new terms introduced anywhere in that surface should
be added here first.

General collection terms also live in `doc/system_requirements.md` and
`doc/design/glossary.md`; this glossary is scoped to the initialization
domain and does not duplicate them except where the init process gives a
term a more specific meaning.

## EventStorming building blocks

### Actor

A party that triggers work in the process. This domain has exactly one:
the **Ansible Operator** — the administrator or automation system running
the `exasol_init` playbook, authenticated as an Exasol account via
`login_user`/`login_password`.

### Command

An imperative request to change state, named as `Verb Noun` (for example
*Create Role*, *Grant Schema Privilege*). Every parameter list item passed
to `exasol_init` (one entry in `roles`, `users`, `role_grants`, `schemas`,
`grants`, `scripts`) becomes one Command.

### Event

A fact that already happened, named in the past tense (for example
*Role Created*, *Schema Privilege Granted*). `exasol_init` does not persist
events explicitly; the event is the SQL statement having been executed, and
its evidence is `executed_queries` plus the row it produces in the
corresponding Exasol system table (Read Model).

### Aggregate

The consistency boundary that accepts one kind of Command and decides
whether it produces an Event. This domain has six: **Role**, **User**,
**Schema**, **Role Assignment**, **Schema Privilege Grant**, **Init Script**
— defined below — plus the **Initialization Run** process manager that
sequences them.

### Policy

A reactive rule of the form "whenever \<event(s)\> then \<command\>" that
connects one Aggregate's Event to another Aggregate's Command. This domain
has two hard synchronization points:

* *Whenever a Role and a User both exist, assign the requested role grants.*
* *Whenever a Role/User grantee and a Schema both exist, apply the requested
  schema privilege grants.*

and one convention-driven ordering policy:

* *Once schema privilege grants are applied, execute init scripts.*

### Read Model

An Exasol system (`EXA_*`) view that `exasol_init` queries to decide whether
a Command is a no-op. Idempotency in this domain is defined entirely in
terms of Read Models — a Command is only executed when the Read Model shows
the requested state does not already hold. See
[Read Models used by `exasol_init`](#read-models-used-by-exasol_init) below.

## Aggregates

### Role

An Exasol authorization principal that groups privileges and can be granted
to Users or other Roles. Backed by `CREATE ROLE` / `DROP ROLE`. Existing
lifecycle vocabulary (`state`, `cascade`, exact identifier handling) is
defined by `specs/ansible_playbook/exasol_role_ansible_playbook.feature` and
reused unchanged by `exasol_init`'s `roles` parameter.

### User

An Exasol account that can authenticate and, once granted `CREATE SESSION`,
open a connection. Backed by `CREATE USER` / `ALTER USER` / `DROP USER`.
Existing lifecycle vocabulary (`authentication_method`, `password`,
`ldap_dn`, `update_password`, `create_session`, `cascade`) is defined by
`specs/ansible_playbook/exasol_user_ansible_playbook.feature` and reused
unchanged by `exasol_init`'s `users` parameter.

### Schema

A namespace that owns tables, views, and other schema objects, and has
exactly one owning User at any time (defaulting to whichever account creates
it). Backed by `CREATE SCHEMA` / `ALTER SCHEMA ... CHANGE OWNER` /
`DROP SCHEMA`. New to this domain; the reusable lifecycle logic lives in
`exasol/ansible_modules/common_schema.py`.

### Role Assignment

The relationship formed by granting a Role to a User (or to another Role).
Backed by `GRANT <role> TO <grantee>` / `REVOKE <role> FROM <grantee>`, and
observed through the `EXA_DBA_ROLE_GRANTS` Read Model. Expressed as one
`role_grants` list item: `{role, user, state}`.

### Schema Privilege Grant

An object-level privilege granted on a Schema to a User or Role. Backed by
`GRANT <privilege> ON SCHEMA <schema> TO <grantee>` /
`REVOKE <privilege> ON SCHEMA <schema> FROM <grantee>`, and observed through
the `EXA_DBA_OBJ_PRIVS` Read Model. Expressed as one `grants` list item:
`{schema, privilege, grantee, state}`. This is distinct from **Role
Assignment** because Exasol itself uses different SQL grammar and different
system tables for granting a role versus granting an object privilege.

### Privilege

The value object naming what a Schema Privilege Grant authorizes:
`ALL`, `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `INDEX`,
`REFERENCES`, or `EXECUTE`.

### Init Script

A trusted-operator SQL statement executed against an already-initialized
Schema, in the same trust model as `exasol_query`
(`doc/design/security/tier_segregation_and_trusted_operator_boundary.md`):
not sandboxed, not automatically redacted, and not reconciled against
existing state — it simply runs. Expressed as one `scripts` list entry (raw
SQL text).

### Initialization Run

The process manager implemented by the `exasol_init` module. It has no
Exasol-side identity of its own; it exists only as the ordered sequence of
Commands it issues to the Aggregates above over a single Exasol connection.

An Initialization Run executes in **two passes** so that one call can safely
mix `state: absent` and `state: present` items across phases:

1. **Teardown pass** — every list item requesting `state: absent`, in
   reverse dependency order: Schema Privilege Grants, Role Assignments,
   Schemas, Users, Roles.
2. **Reconciliation pass** — every list item requesting `state: present`
   (the default), plus all `scripts`, in forward dependency order: Roles,
   Users, Role Assignments, Schemas, Schema Privilege Grants, Init Scripts.

This means a single run can tear down stale grants before recreating them
with different parameters, without the operator having to split the work
into two separate `exasol_init` tasks.

## Shared lifecycle vocabulary

These terms already exist in `exasol_user`/`exasol_role`/`exasol_query` and
apply unchanged inside `exasol_init`:

### State (`present` / `absent`)

Declares whether an Aggregate instance should exist after the run. Default
is `present` for every list item except `scripts`, which has no `state`
(scripts are executed, not reconciled — see **Init Script** above).

### Cascade

When dropping a Role, User, or Schema, `cascade: true` appends `CASCADE` so
Exasol also drops objects that depend on it. Mirrors
`exasol_role`/`exasol_user`'s existing `cascade` parameter.

### Check Mode

When the Ansible task runs with `check_mode: true`, `exasol_init` plans and
returns the same `executed_queries` it would otherwise run, across every
phase, but does not execute any of them and does not open a write
transaction. Mirrors the check-mode contract already defined in
`specs/ansible_playbook/exasol_user_ansible_playbook.feature` and
`specs/ansible_playbook/exasol_role_ansible_playbook.feature`.

### Idempotent Reconciliation

A Command is only translated into executed SQL when the relevant Read Model
shows the requested state does not already hold. Re-running `exasol_init`
with the same parameters against an already-initialized environment reports
`changed: false` for every reconciled phase (`roles`, `users`,
`role_grants`, `schemas`, `grants`) and `changed: true` for `scripts` only if
scripts are supplied (scripts are always executed, per **Init Script**).

### Exact Identifier

Role, User, and Schema names are treated as exact Exasol identifier values
(case- and character-preserving), using the same
`exasol/ansible_modules/common_identifier_validation.py` helpers already
used by `exasol_role`/`exasol_user`. See
`specs/ansible_playbook/exasol_user_ansible_playbook.feature`'s
`@exasol-user-preserves-exact-identifier` scenario for the existing contract
this reuses.

### Secret-Safe Result

Passwords and LDAP distinguished names supplied in `users` never appear in
`exasol_init`'s result or in `executed_queries`, mirroring
`req~keep-audit-output-secret-safe~1` in `doc/system_requirements.md`.

## Read Models used by `exasol_init`

| Read Model             | Backs Aggregate         | Queried to decide…                          |
|-------------------------|--------------------------|----------------------------------------------|
| `EXA_ALL_ROLES`          | Role                     | whether `CREATE ROLE` / `DROP ROLE` is a no-op |
| `EXA_DBA_USERS`          | User                     | whether `CREATE USER` / `ALTER USER` is a no-op |
| `EXA_ALL_SCHEMAS`        | Schema                   | whether `CREATE SCHEMA` / owner change is a no-op |
| `EXA_DBA_ROLE_GRANTS`    | Role Assignment          | whether `GRANT <role> TO <grantee>` is a no-op |
| `EXA_DBA_OBJ_PRIVS`      | Schema Privilege Grant   | whether `GRANT <privilege> ON SCHEMA` is a no-op |

## Open Issues

* `Privilege` currently only covers schema-level grants. Object-level grants
  scoped to individual tables/views are out of scope for `exasol_init` until
  a dedicated need is identified.
* No standalone `exasol_schema` or `exasol_grants` Ansible module exists yet;
  `common_schema.py` and the grant planners are internal to `exasol_init`
  until that surface is requested (see `doc/system_requirements.md`).
