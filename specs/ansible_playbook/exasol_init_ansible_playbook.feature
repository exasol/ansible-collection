Feature: exasol-init specification
  Initialize an Exasol environment (roles, users, role grants, schemas,
  schema privilege grants, and init scripts) from Ansible playbooks, in the
  dependency order discovered in specs/diagrams/exasol_init_process_diagram.md
  and specs/glossary/exasol_init_glossary.md.

  @exasol-init-full-environment-happy-path
  Scenario: Initialize a full environment in dependency order
    Given an Exasol database is reachable at localhost
    And role "REPORTER" does not exist in EXA_ALL_ROLES
    And user "REPORT_USER" does not exist in EXA_ALL_USERS
    And schema "REPORT_SCHEMA" does not exist in EXA_ALL_SCHEMAS
    When exasol_init runs with:
      | roles                | users                                                          | role_grants                             | schemas                                     | grants                                                  | scripts                                                     |
      | [{name: REPORTER}]   | [{name: REPORT_USER, password: Initial_Secret_42}]             | [{role: REPORTER, user: REPORT_USER}]   | [{name: REPORT_SCHEMA, owner: REPORT_USER}] | [{schema: REPORT_SCHEMA, privilege: SELECT, grantee: REPORTER}] | ["CREATE TABLE REPORT_SCHEMA.EVENTS (ID INT)"]              |
    Then changed is true
    And executed_queries equals:
      | sql                                                                |
      | CREATE ROLE "REPORTER"                                             |
      | CREATE USER "REPORT_USER" IDENTIFIED BY "********"                |
      | GRANT CREATE SESSION TO "REPORT_USER"                             |
      | GRANT "REPORTER" TO "REPORT_USER"                                 |
      | CREATE SCHEMA "REPORT_SCHEMA"                                     |
      | ALTER SCHEMA "REPORT_SCHEMA" CHANGE OWNER "REPORT_USER"           |
      | GRANT SELECT ON SCHEMA "REPORT_SCHEMA" TO "REPORTER"              |
      | CREATE TABLE REPORT_SCHEMA.EVENTS (ID INT)                        |
    And role "REPORTER" exists in EXA_ALL_ROLES
    And user "REPORT_USER" exists in EXA_ALL_USERS
    And EXA_DBA_ROLE_GRANTS contains one row where GRANTEE equals "REPORT_USER" and GRANTED_ROLE equals "REPORTER"
    And EXA_ALL_SCHEMAS.SCHEMA_OWNER for "REPORT_SCHEMA" equals "REPORT_USER"
    And EXA_DBA_OBJ_PRIVS contains one row where OBJECT_NAME equals "REPORT_SCHEMA" and GRANTEE equals "REPORTER" and PRIVILEGE equals "SELECT"
    And table "REPORT_SCHEMA.EVENTS" exists

  @exasol-init-schema-owner-assigned-after-user-created
  Scenario: Schema owner reassignment depends only on the owning user
    Given an Exasol database is reachable at localhost
    And user "OWNER_USER" does not exist in EXA_ALL_USERS
    And schema "OWNED_SCHEMA" does not exist in EXA_ALL_SCHEMAS
    When exasol_init runs with:
      | users                                                | schemas                                    |
      | [{name: OWNER_USER, password: Initial_Secret_42}]    | [{name: OWNED_SCHEMA, owner: OWNER_USER}]  |
    Then changed is true
    And executed_queries equals:
      | sql                                                          |
      | CREATE USER "OWNER_USER" IDENTIFIED BY "********"           |
      | GRANT CREATE SESSION TO "OWNER_USER"                        |
      | CREATE SCHEMA "OWNED_SCHEMA"                                |
      | ALTER SCHEMA "OWNED_SCHEMA" CHANGE OWNER "OWNER_USER"       |
    And EXA_ALL_SCHEMAS.SCHEMA_OWNER for "OWNED_SCHEMA" equals "OWNER_USER"

  @exasol-init-grants-wait-for-roles-users-and-schemas
  Scenario: Schema privilege grants only run once their role, user, and schema all exist
    Given an Exasol database is reachable at localhost
    And role "AUDITOR" does not exist in EXA_ALL_ROLES
    And schema "AUDIT_SCHEMA" does not exist in EXA_ALL_SCHEMAS
    When exasol_init runs with:
      | roles              | schemas                    | grants                                                       |
      | [{name: AUDITOR}]  | [{name: AUDIT_SCHEMA}]     | [{schema: AUDIT_SCHEMA, privilege: SELECT, grantee: AUDITOR}] |
    Then changed is true
    And executed_queries equals:
      | sql                                                    |
      | CREATE ROLE "AUDITOR"                                  |
      | CREATE SCHEMA "AUDIT_SCHEMA"                           |
      | GRANT SELECT ON SCHEMA "AUDIT_SCHEMA" TO "AUDITOR"     |
    And the grant statement is executed after both the role and schema creation statements

  @exasol-init-scripts-run-after-grants
  Scenario: Init scripts execute only after grants are applied
    Given an Exasol database is reachable at localhost
    And schema "CONTENT_SCHEMA" does not exist in EXA_ALL_SCHEMAS
    And role "CONTENT_READER" does not exist in EXA_ALL_ROLES
    When exasol_init runs with:
      | roles                    | schemas                 | grants                                                               | scripts                                                |
      | [{name: CONTENT_READER}] | [{name: CONTENT_SCHEMA}] | [{schema: CONTENT_SCHEMA, privilege: SELECT, grantee: CONTENT_READER}] | ["CREATE TABLE CONTENT_SCHEMA.ARTICLES (ID INT)"]    |
    Then changed is true
    And executed_queries equals:
      | sql                                                                |
      | CREATE ROLE "CONTENT_READER"                                      |
      | CREATE SCHEMA "CONTENT_SCHEMA"                                    |
      | GRANT SELECT ON SCHEMA "CONTENT_SCHEMA" TO "CONTENT_READER"       |
      | CREATE TABLE CONTENT_SCHEMA.ARTICLES (ID INT)                     |
    And the script statement is the last executed query

  @exasol-init-apply-unchanged-is-idempotent
  Scenario: Re-applying an identical environment makes no further changes
    Given an Exasol database is reachable at localhost
    And role "IDEMPOTENT_ROLE" already exists in EXA_ALL_ROLES
    And user "IDEMPOTENT_USER" already exists after exasol_init created it with password "Initial_Secret_42"
    And user "IDEMPOTENT_USER" already has role "IDEMPOTENT_ROLE" granted
    And schema "IDEMPOTENT_SCHEMA" already exists owned by "IDEMPOTENT_USER"
    And "IDEMPOTENT_ROLE" already has SELECT granted on schema "IDEMPOTENT_SCHEMA"
    When exasol_init runs again with:
      | roles                     | users                                                       | role_grants                                          | schemas                                          | grants                                                             |
      | [{name: IDEMPOTENT_ROLE}] | [{name: IDEMPOTENT_USER, password: Initial_Secret_42, update_password: on_create}] | [{role: IDEMPOTENT_ROLE, user: IDEMPOTENT_USER}] | [{name: IDEMPOTENT_SCHEMA, owner: IDEMPOTENT_USER}] | [{schema: IDEMPOTENT_SCHEMA, privilege: SELECT, grantee: IDEMPOTENT_ROLE}] |
    Then changed is false
    And executed_queries equals []

  @exasol-init-check-mode-predicts-full-plan
  Scenario: Check mode predicts the full ordered plan without writing
    Given an Exasol database is reachable at localhost
    And role "CHECK_ROLE" does not exist in EXA_ALL_ROLES
    And user "CHECK_USER" does not exist in EXA_ALL_USERS
    And schema "CHECK_SCHEMA" does not exist in EXA_ALL_SCHEMAS
    When exasol_init runs in check mode with:
      | roles              | users                                                       | role_grants                             | schemas                                     | grants                                                        | scripts                                          |
      | [{name: CHECK_ROLE}] | [{name: CHECK_USER, password: Check_Secret_42}]           | [{role: CHECK_ROLE, user: CHECK_USER}]  | [{name: CHECK_SCHEMA, owner: CHECK_USER}]   | [{schema: CHECK_SCHEMA, privilege: SELECT, grantee: CHECK_ROLE}] | ["CREATE TABLE CHECK_SCHEMA.T (ID INT)"]       |
    Then changed is true
    And executed_queries equals:
      | sql                                                          |
      | CREATE ROLE "CHECK_ROLE"                                     |
      | CREATE USER "CHECK_USER" IDENTIFIED BY "********"           |
      | GRANT CREATE SESSION TO "CHECK_USER"                        |
      | GRANT "CHECK_ROLE" TO "CHECK_USER"                          |
      | CREATE SCHEMA "CHECK_SCHEMA"                                |
      | ALTER SCHEMA "CHECK_SCHEMA" CHANGE OWNER "CHECK_USER"       |
      | GRANT SELECT ON SCHEMA "CHECK_SCHEMA" TO "CHECK_ROLE"       |
      | CREATE TABLE CHECK_SCHEMA.T (ID INT)                        |
    And role "CHECK_ROLE" still does not exist in EXA_ALL_ROLES
    And user "CHECK_USER" still does not exist in EXA_ALL_USERS
    And schema "CHECK_SCHEMA" still does not exist in EXA_ALL_SCHEMAS
    And the module result does not contain "Check_Secret_42"

  @exasol-init-partial-environment-roles-and-users-only
  Scenario: Optional phases are skipped when their parameters are omitted
    Given an Exasol database is reachable at localhost
    And role "MINIMAL_ROLE" does not exist in EXA_ALL_ROLES
    And user "MINIMAL_USER" does not exist in EXA_ALL_USERS
    When exasol_init runs with:
      | roles                | users                                                |
      | [{name: MINIMAL_ROLE}] | [{name: MINIMAL_USER, password: Initial_Secret_42}] |
    Then changed is true
    And executed_queries equals:
      | sql                                                   |
      | CREATE ROLE "MINIMAL_ROLE"                            |
      | CREATE USER "MINIMAL_USER" IDENTIFIED BY "********"  |
      | GRANT CREATE SESSION TO "MINIMAL_USER"               |
    And no schema, grant, or script phase produces any statement

  @exasol-init-teardown-drops-in-reverse-dependency-order
  Scenario: Tearing down an environment reverses the dependency order
    Given an Exasol database is reachable at localhost
    And role "TEARDOWN_ROLE" already exists in EXA_ALL_ROLES
    And user "TEARDOWN_USER" already exists after exasol_init created it with password "Initial_Secret_42"
    And user "TEARDOWN_USER" already has role "TEARDOWN_ROLE" granted
    And schema "TEARDOWN_SCHEMA" already exists owned by "TEARDOWN_USER"
    And "TEARDOWN_ROLE" already has SELECT granted on schema "TEARDOWN_SCHEMA"
    When exasol_init runs with:
      | roles                              | users                                          | role_grants                                                    | schemas                                              | grants                                                                          |
      | [{name: TEARDOWN_ROLE, state: absent, cascade: true}] | [{name: TEARDOWN_USER, state: absent, cascade: true}] | [{role: TEARDOWN_ROLE, user: TEARDOWN_USER, state: absent}] | [{name: TEARDOWN_SCHEMA, state: absent, cascade: true}] | [{schema: TEARDOWN_SCHEMA, privilege: SELECT, grantee: TEARDOWN_ROLE, state: absent}] |
    Then changed is true
    And executed_queries equals:
      | sql                                                                        |
      | REVOKE SELECT ON SCHEMA "TEARDOWN_SCHEMA" FROM "TEARDOWN_ROLE"            |
      | REVOKE "TEARDOWN_ROLE" FROM "TEARDOWN_USER"                               |
      | DROP SCHEMA "TEARDOWN_SCHEMA" CASCADE                                     |
      | DROP USER "TEARDOWN_USER" CASCADE                                         |
      | DROP ROLE "TEARDOWN_ROLE" CASCADE                                         |
    And role "TEARDOWN_ROLE" no longer exists in EXA_ALL_ROLES
    And user "TEARDOWN_USER" no longer exists in EXA_ALL_USERS
    And schema "TEARDOWN_SCHEMA" no longer exists in EXA_ALL_SCHEMAS

  @exasol-init-secrets-are-not-exposed
  Scenario: Passwords and LDAP distinguished names are never exposed
    Given an Exasol database is reachable at localhost
    And user "SECRET_USER" does not exist in EXA_ALL_USERS
    And user "SECRET_LDAP_USER" does not exist in EXA_ALL_USERS
    When exasol_init runs with:
      | users                                                                                                                                          |
      | [{name: SECRET_USER, password: Initial_Secret_42}, {name: SECRET_LDAP_USER, authentication_method: ldap, ldap_dn: "cn=secret,dc=authorization,dc=exasol,dc=com"}] |
    Then changed is true
    And the module result does not contain "Initial_Secret_42"
    And the module result does not contain "cn=secret,dc=authorization,dc=exasol,dc=com"
