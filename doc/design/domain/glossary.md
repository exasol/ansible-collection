# Exasol Ansible Collection Glossary

This chapter defines domain-specific terms used in the documentation.

Terms derived from the Given/When/Then vocabulary used across
`specs/ansible_modules/*.feature` (module-runtime specifications) and
`specs/ansible_playbook/*.feature` (playbook-level specifications)

General System Requirements are defined in [System Requirements](../../system_requirements.md).

| Term | Meaning |
|------|---------|
| Ansible Operator | The actor who runs a playbook or module task against Exasol; the sole actor across every scenario in both spec folders. |
| Exasol database / Exasol cluster | The target Exasol instance, reachable at `login_host`, that a scenario's `Given` step establishes as available before any `When` step runs. |
| Ansible module | The thin `plugins/modules/exasol_*.py` entry point that Ansible invokes; parses `AnsibleModule` parameters and calls the matching runtime. |
| Runtime | The reusable `exasol.ansible_modules.exasol_*` Python package that a module wraps; module-runtime specs exercise it directly, playbook specs exercise it through the Ansible module. |
| Connection parameters | The shared `login_host`, `login_port`, `login_user`, `login_password`, `login_db`/`login_schema`, `autocommit`, `fetch_size`, `compression`, `validate_certs`, `ca_cert`, `certificate_fingerprint`, and `client_kwargs` options every module accepts. |
| State | The declarative `present` or `absent` value an operator requests for a schema, user, role, or grant; the runtime reconciles observed Exasol state toward it. |
| Changed | The boolean result field reporting whether a scenario's run altered Exasol state (or, in check mode, would alter it). |
| Check mode | A dry-run invocation that predicts the same statements and `changed` value a real run would produce, without executing any write statement. |
| Check-mode no-action prediction | A check-mode result where the observed state already matches the desired state: `changed=false`, the observed `exists` value is preserved, and `executed_queries` is empty (metadata queries used to observe state may still run). Reported when an object already exists under `state=present`, or already does not exist under `state=absent`. |
| Executed queries | The `executed_queries` result field: the SQL statements a scenario actually ran, in order, or — for check mode and `exasol_script` specifically — the statements or script predicted to run. |
| Query result / Query all results | `query_result` (rows from the last statement) and `query_all_results` (one row list per statement) returned by `exasol_query` and `exasol_script`. |
| Rowcount / Execution time | Per-statement `rowcount` and `execution_time_ms` values reported alongside executed queries. |
| Read-only statement | A statement (`SELECT`, `DESCRIBE`, `SHOW`, `VALUES`, ...) that does not change Exasol state; a scenario made up only of these reports `changed=false` and executes normally even in check mode. |
| Script | A single string, accepted by `exasol_script`, containing one or more SQL statements executed in order on one connection via pyexasol's `execute_sql_script`. |
| Script body | An Exasol object definition (for example `CREATE ... SCRIPT`) whose text may contain embedded semicolons that do not terminate the statement; ended by a standalone `/` line instead. |
| Statement batch | A list of SQL statements, accepted by `exasol_query`, executed in the supplied order on one connection. |
| Bound arguments | `positional_args` (`?` placeholders) or `named_args` (`:name` placeholders) bound into a single `exasol_query` statement; rejected for statement batches and not accepted at all by `exasol_script`. |
| Schema | An Exasol schema, identified by name, with an optional owner, comment, and raw size limit, managed by `exasol_schema`. |
| Owner | The Exasol user or role that owns a schema; reconciled through `ALTER SCHEMA ... CHANGE OWNER` when it differs from the requested value. |
| Raw size limit | A schema's storage quota, reconciled through `ALTER SCHEMA ... SET RAW_SIZE_LIMIT`. |
| Rename | Changing a schema's name via `RENAME SCHEMA`, requested through the `new_name` option. |
| Cascade | The explicit `cascade` option that appends `CASCADE` to a `DROP SCHEMA`, `DROP USER`, or `DROP ROLE` statement; without it, dropping a non-empty object fails safely. |
| User | An Exasol login identity, identified by name, with a password or LDAP authentication method and optional session-grant and cascade-drop behavior, managed by `exasol_user`. |
| Password / update_password | A user's authentication secret and the `update_password` option (`on_create` sets it only when creating the user; `always` updates it on every run) controlling whether an existing password is rotated; applies when `authentication_method` is `password`. |
| Authentication method / LDAP DN | The `authentication_method` option (`password` or `ldap`) selecting a user's credential mechanism, and `ldap_dn` — the LDAP distinguished name bound to the user via `ALTER USER ... IDENTIFIED AT LDAP AS` — supplied when `authentication_method` is `ldap`. |
| Session grant | The `GRANT CREATE SESSION` statement issued alongside `CREATE USER` so a newly created user can log in, controlled by the `create_session` option (default `true`). |
| Role | A named Exasol privilege container, identified by name, managed by `exasol_role`; users and other roles can be granted membership in it. |
| Grants | Privilege assignments to a user or role, managed by `exasol_grants`: `system_privileges` (server-wide privileges such as `CREATE SESSION`), `object_privileges` (a batch of schema-scoped privilege requests, each naming a `schema`, an optional `object` and `object_type`, and its `privileges`), and their shared `state` (`present` grants, `absent` revokes). |
| Object type | The `object_type` option on an `object_privileges` entry (`function`, `script`, `table`, `view`, or `virtual_schema`) disambiguating same-named schema objects; optional when `object` is omitted or unambiguous. |
| Principal / Principal type | The user or role a grant scenario targets, and whether it is a `user` or a `role`; a scenario must supply exactly one, never both. |
| Exact identifier | A user, role, or schema name preserved exactly as supplied, including case and special characters, instead of being normalized or uppercased. |
| Info | The read-only server facts (`version`, `database_name`, `cluster_size`) `exasol_info` gathers; always reports `changed=false`. |
| Authentication error | A sanitized failure message returned when Exasol login fails, replacing the underlying driver error so no attempted credential value is exposed. |
| Sanitized error / Secret redaction | The rule that any error message returned to Ansible must have known secret values (`login_password`, sensitive `client_kwargs`, sensitive `named_args`) replaced before it reaches module output. |
| Catalog view | An Exasol system view such as `EXA_ALL_SCHEMAS`, `EXA_SCHEMAS`, `EXA_ALL_USERS`, `EXA_ALL_ROLES`, `EXA_ALL_OBJECT_SIZES`, `EXA_ALL_SCRIPTS`, `EXA_DBA_SYS_PRIVS`, `EXA_DBA_OBJ_PRIVS`, or `EXA_METADATA` that a scenario's `Then` step queries directly to verify Exasol's resulting state, independent of the runtime under test. |
| Scenario / Scenario ID | One Gherkin `Scenario:` in a `.feature` file, tagged with a unique `@scenario-id` that a matching acceptance test declares via `pytest.mark.scenario_id` to keep specs and tests synchronized. |
