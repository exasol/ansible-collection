Feature: exasol-grants specification
  Manage Exasol database grants from Ansible playbooks.

  Background:
    Given an Exasol database is reachable at localhost

  @exasol-grants-grant-missing-system-privilege
  Scenario: Grant missing system privilege
    And user "ALICE" exists without CREATE SESSION
    When exasol_grants runs with:
      | user  | system_privileges | state   |
      | ALICE | CREATE SESSION    | present |
    Then changed is true
    And principal equals "ALICE"
    And principal_type equals "user"
    And executed_queries equals:
      | sql                             |
      | GRANT CREATE SESSION TO "ALICE" |
    And EXA_DBA_SYS_PRIVS contains CREATE SESSION for "ALICE"

  @exasol-grants-system-privilege-idempotent
  Scenario: Existing system privilege is unchanged
    And user "ALICE" already has CREATE SESSION
    When exasol_grants runs with:
      | user  | system_privileges | state   |
      | ALICE | CREATE SESSION    | present |
    Then changed is false
    And executed_queries equals []

  @exasol-grants-grant-multiple-system-and-object-privileges
  Scenario: Grant multiple system and object privileges
    And user "ALICE" exists without CREATE SESSION
    And schema "APP_SCHEMA" contains table "FACT_SALES"
    When exasol_grants runs with multiple system and object privileges
    Then changed is true
    And executed_queries contains:
      | sql                                                   |
      | GRANT CREATE SESSION TO "ALICE"                       |
      | GRANT CREATE SCHEMA TO "ALICE"                        |
      | GRANT USAGE ON "APP_SCHEMA" TO "ALICE"               |
      | GRANT SELECT ON "APP_SCHEMA"."FACT_SALES" TO "ALICE" |
      | GRANT INSERT ON "APP_SCHEMA"."FACT_SALES" TO "ALICE" |
    And EXA_DBA_SYS_PRIVS contains CREATE SESSION for "ALICE"
    And EXA_DBA_SYS_PRIVS contains CREATE SCHEMA for "ALICE"
    And EXA_DBA_OBJ_PRIVS contains USAGE on "APP_SCHEMA" for "ALICE"
    And EXA_DBA_OBJ_PRIVS contains SELECT on "APP_SCHEMA"."FACT_SALES" for "ALICE"
    And EXA_DBA_OBJ_PRIVS contains INSERT on "APP_SCHEMA"."FACT_SALES" for "ALICE"

  @exasol-grants-revoke-existing-schema-object-privilege
  Scenario: Revoke existing schema object privilege
    And user "ALICE" has USAGE on schema "APP_SCHEMA"
    When exasol_grants runs with:
      | user  | schema     | object_privileges | state  |
      | ALICE | APP_SCHEMA | USAGE             | absent |
    Then changed is true
    And executed_queries equals:
      | sql                                             |
      | REVOKE USAGE ON "APP_SCHEMA" FROM "ALICE"      |
    And EXA_DBA_OBJ_PRIVS no longer contains USAGE on "APP_SCHEMA" for "ALICE"

  @exasol-grants-absent-schema-object-privilege-idempotent
  Scenario: Missing schema object privilege is unchanged when absent
    And user "ALICE" does not have USAGE on schema "APP_SCHEMA"
    When exasol_grants runs with:
      | user  | schema     | object_privileges | state  |
      | ALICE | APP_SCHEMA | USAGE             | absent |
    Then changed is false
    And executed_queries equals []

  @exasol-grants-check-mode-predicts-system-grant
  Scenario: Check mode predicts system grant
    And user "ALICE" exists without CREATE SESSION
    When exasol_grants runs in check mode with:
      | user  | system_privileges | state   |
      | ALICE | CREATE SESSION    | present |
    Then changed is true
    And executed_queries equals:
      | sql                             |
      | GRANT CREATE SESSION TO "ALICE" |
    And EXA_DBA_SYS_PRIVS still does not contain CREATE SESSION for "ALICE"

  @exasol-grants-reject-mutually-exclusive-principals
  Scenario: Reject mutually exclusive principals
    When exasol_grants runs with both user and role
    Then the module fails with a validation error
    And no privilege-changing SQL is generated

  @exasol-grants-grant-role-membership-to-user
  Scenario: Grant role membership to a user
    Given an Exasol database is reachable at localhost
    And user "ALICE" is not a member of role "APP_ROLE"
    When exasol_grants grants APP_ROLE to ALICE
    Then changed is true
    And EXA_DBA_ROLE_PRIVS contains "APP_ROLE" for "ALICE"

  @exasol-grants-role-membership-idempotent
  Scenario: Existing role membership is unchanged
    Given an Exasol database is reachable at localhost
    And user "ALICE" is already a member of role "APP_ROLE"
    When exasol_grants grants APP_ROLE to ALICE again
    Then changed is false
    And executed_queries equals []

  @exasol-grants-revoke-role-membership
  Scenario: Revoke existing role membership
    Given an Exasol database is reachable at localhost
    And user "ALICE" is a member of role "APP_ROLE"
    When exasol_grants revokes APP_ROLE from ALICE
    Then changed is true
    And EXA_DBA_ROLE_PRIVS no longer contains "APP_ROLE" for "ALICE"

  @exasol-grants-check-mode-role-membership
  Scenario: Check mode predicts role membership grant
    Given an Exasol database is reachable at localhost
    And user "ALICE" is not a member of role "APP_ROLE"
    When exasol_grants predicts granting APP_ROLE to ALICE in check mode
    Then changed is true
    And EXA_DBA_ROLE_PRIVS still does not contain "APP_ROLE" for "ALICE"

  @exasol-grants-insufficient-privilege-sanitized-error
  Scenario: Insufficient-privilege failure surfaces a sanitized error
    Given an Exasol database is reachable at localhost
    And the connecting user lacks GRANT ANY PRIVILEGE
    When exasol_grants attempts a system privilege grant
    Then the module fails with a sanitized authorization error
    And no raw driver exception or password is exposed
