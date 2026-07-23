Feature: exasol-grants Ansible module runtime specification
  Manage Exasol database grants directly through the exasol_grants Python
  runtime helpers.

  @exasol-grants-grant-missing-system-privilege
  Scenario: Grant missing system privilege
    Given an Exasol database is reachable at localhost
    And user "ALICE" exists without CREATE SESSION
    When the grants runtime runs with CREATE SESSION present
    Then changed is true
    And principal equals the generated user name
    And principal_type equals "user"
    And executed_queries equals a single GRANT CREATE SESSION statement
    And EXA_DBA_SYS_PRIVS contains CREATE SESSION for the user

  @exasol-grants-system-privilege-idempotent
  Scenario: Existing system privilege is unchanged
    Given an Exasol database is reachable at localhost
    And user "ALICE" already has CREATE SESSION
    When the grants runtime runs with CREATE SESSION present
    Then changed is false
    And executed_queries equals []
    And EXA_DBA_SYS_PRIVS still contains one CREATE SESSION grant

  @exasol-grants-grant-multiple-system-and-object-privileges
  Scenario: Grant multiple system and object privileges
    Given an Exasol database is reachable at localhost
    And user "ALICE" exists without CREATE SESSION
    And schema "APP_SCHEMA" contains table "FACT_SALES"
    When the grants runtime runs with multiple system and object privileges
    Then changed is true
    And executed_queries contains the missing GRANT statements
    And the requested privileges exist in Exasol metadata

  @exasol-grants-revoke-existing-schema-object-privilege
  Scenario: Revoke existing schema object privilege
    Given an Exasol database is reachable at localhost
    And user "ALICE" has USAGE on schema "APP_SCHEMA"
    When the grants runtime runs with schema USAGE absent
    Then changed is true
    And executed_queries equals a single REVOKE USAGE statement
    And EXA_DBA_OBJ_PRIVS no longer contains USAGE on the schema for the user

  @exasol-grants-absent-schema-object-privilege-idempotent
  Scenario: Missing schema object privilege is unchanged when absent
    Given an Exasol database is reachable at localhost
    And user "ALICE" does not have USAGE on schema "APP_SCHEMA"
    When the grants runtime runs with schema USAGE absent
    Then changed is false
    And executed_queries equals []

  @exasol-grants-check-mode-predicts-system-grant
  Scenario: Check mode predicts system grant
    Given an Exasol database is reachable at localhost
    And user "ALICE" exists without CREATE SESSION
    When the grants runtime runs in check mode with CREATE SESSION present
    Then changed is true
    And executed_queries equals a single GRANT CREATE SESSION statement
    And EXA_DBA_SYS_PRIVS still does not contain CREATE SESSION for the user

  @exasol-grants-reject-mutually-exclusive-principals
  Scenario: Reject mutually exclusive principals
    Given an Exasol database is reachable at localhost
    When the grants runtime runs with both user and role
    Then the runtime fails with a validation error
    And no privilege-changing SQL is generated

  @exasol-grants-grant-role-membership-to-user
  Scenario: Grant role membership to a user
    Given an Exasol database is reachable at localhost
    And user "ALICE" is not a member of role "APP_ROLE"
    When the grants runtime runs with role membership present
    Then changed is true
    And executed_queries equals a single GRANT role statement
    And EXA_DBA_ROLE_PRIVS contains "APP_ROLE" for "ALICE"

  @exasol-grants-role-membership-idempotent
  Scenario: Existing role membership is unchanged
    Given an Exasol database is reachable at localhost
    And user "ALICE" is already a member of role "APP_ROLE"
    When the grants runtime runs with role membership present
    Then changed is false
    And executed_queries equals []

  @exasol-grants-revoke-role-membership
  Scenario: Revoke existing role membership
    Given an Exasol database is reachable at localhost
    And user "ALICE" is a member of role "APP_ROLE"
    When the grants runtime runs with role membership absent
    Then changed is true
    And executed_queries equals a single REVOKE role statement
    And EXA_DBA_ROLE_PRIVS no longer contains "APP_ROLE" for "ALICE"

  @exasol-grants-check-mode-role-membership
  Scenario: Check mode predicts role membership grant
    Given an Exasol database is reachable at localhost
    And user "ALICE" is not a member of role "APP_ROLE"
    When the grants runtime runs in check mode with role membership present
    Then changed is true
    And EXA_DBA_ROLE_PRIVS still does not contain "APP_ROLE" for "ALICE"

  @exasol-grants-grant-missing-system-privilege-to-role
  Scenario: Grant missing system privilege to a role
    Given an Exasol database is reachable at localhost
    And role "APP_ROLE" exists without CREATE SESSION
    When the grants runtime runs with CREATE SESSION present for the role
    Then changed is true
    And executed_queries equals a single role-principal GRANT statement
    And EXA_DBA_SYS_PRIVS contains CREATE SESSION for "APP_ROLE"

  @exasol-grants-grant-script-execute-privilege
  Scenario: Grant EXECUTE on a script object
    Given an Exasol database is reachable at localhost
    And schema "APP_SCHEMA" contains script "CALC_TOTAL"
    When the grants runtime runs with object_type script
    Then changed is true
    And executed_queries equals a SCRIPT object GRANT statement

  @exasol-grants-grant-view-select-privilege
  Scenario: Grant SELECT on a view object
    Given an Exasol database is reachable at localhost
    And schema "APP_SCHEMA" contains view "SALES_VIEW"
    When the grants runtime runs with object_type view
    Then changed is true
    And executed_queries equals a VIEW object GRANT statement

  @exasol-grants-check-mode-predicts-no-action-when-granted
  Scenario: Check mode predicts no action when privilege already granted
    Given an Exasol database is reachable at localhost
    And user "ALICE" already has CREATE SESSION
    When the grants runtime runs in check mode with CREATE SESSION present
    Then changed is false
    And executed_queries equals []

  @exasol-grants-check-mode-predicts-revoke
  Scenario: Check mode predicts a revoke without executing it
    Given an Exasol database is reachable at localhost
    And user "ALICE" has USAGE on schema "APP_SCHEMA"
    When the grants runtime runs in check mode with schema USAGE absent
    Then changed is true
    And EXA_DBA_OBJ_PRIVS still contains USAGE on "APP_SCHEMA" for "ALICE"

  @exasol-grants-grant-batch-with-some-privileges-already-present
  Scenario: Grant a batch where some privileges already exist
    Given an Exasol database is reachable at localhost
    And user "ALICE" already has CREATE SESSION
    And user "ALICE" does not have CREATE SCHEMA
    When the grants runtime runs with both system privileges present
    Then changed is true
    And executed_queries equals a single GRANT CREATE SCHEMA statement

  @exasol-grants-absent-system-privilege-idempotent
  Scenario: Missing system privilege is unchanged when absent
    Given an Exasol database is reachable at localhost
    And user "ALICE" does not have CREATE SCHEMA
    When the grants runtime runs with CREATE SCHEMA absent
    Then changed is false
    And executed_queries equals []

  @exasol-grants-reject-unsupported-privilege
  Scenario: Reject an unsupported privilege name
    Given an Exasol database is reachable at localhost
    When the grants runtime runs with an unsupported system privilege
    Then the runtime fails with a validation error

  @exasol-grants-reject-empty-request
  Scenario: Reject a request with no privileges
    Given an Exasol database is reachable at localhost
    When the grants runtime runs with no grant requests
    Then the runtime fails with a validation error

  @exasol-grants-preserves-exact-identifier
  Scenario: Grant to an exact-identifier principal
    Given an Exasol database is reachable at localhost
    And exact-identifier role "App+/=Role" exists without CREATE SESSION
    When the grants runtime runs with CREATE SESSION present for that role
    Then changed is true
    And executed_queries preserves the exact role identifier

  @exasol-grants-idempotent-with-different-case-spelling
  Scenario: Grant stays idempotent across case-only spelling changes
    Given an Exasol database is reachable at localhost
    And exact-identifier role "App+/=Role" already has CREATE SESSION
    When the grants runtime runs with different case spelling
    Then changed is false
    And executed_queries equals []

  @exasol-grants-insufficient-privilege-sanitized-error
  Scenario: Insufficient-privilege failure surfaces a sanitized error
    Given an Exasol database is reachable at localhost
    And the connecting user lacks GRANT ANY PRIVILEGE
    When the grants runtime error is normalized
    Then the message is sanitized
    And no raw driver exception is exposed

  @exasol-grants-grant-system-privilege-with-admin-option
  Scenario: Grant system privilege with admin option
    Given an Exasol database is reachable at localhost
    And user "ALICE" exists without SELECT ANY TABLE
    When the grants runtime runs with admin_option true
    Then changed is true
    And executed_queries equals a GRANT statement with WITH ADMIN OPTION
    And EXA_DBA_SYS_PRIVS records admin option for the privilege

  @exasol-grants-grant-mixed-system-privileges-with-admin-options
  Scenario: Grant mixed system privileges with per-privilege admin option
    Given an Exasol database is reachable at localhost
    And user "ALICE" lacks SELECT ANY TABLE and CREATE SESSION
    When the grants runtime runs with per-privilege admin options
    Then changed is true
    And one system privilege is granted with admin option
    And one system privilege is granted without admin option

  @exasol-grants-grant-role-membership-with-admin-option
  Scenario: Grant role membership with admin option
    Given an Exasol database is reachable at localhost
    And user "ALICE" is not a member of role "APP_ROLE"
    When the grants runtime runs with role membership and admin_option true
    Then changed is true
    And executed_queries equals a role GRANT statement with WITH ADMIN OPTION
    And EXA_DBA_ROLE_PRIVS records admin option for the role membership

  @exasol-grants-grant-mixed-role-memberships-with-admin-options
  Scenario: Grant mixed role memberships with per-role admin option
    Given an Exasol database is reachable at localhost
    And user "ALICE" is not a member of roles "APP_READER" and "APP_WRITER"
    When the grants runtime runs with per-role admin options
    Then changed is true
    And one role membership is granted with admin option
    And one role membership is granted without admin option

  @exasol-grants-downgrade-system-privilege-admin-option
  Scenario: Downgrade system privilege admin option
    Given an Exasol database is reachable at localhost
    And user "ALICE" has SELECT ANY TABLE with admin option
    When the grants runtime runs with admin_option false
    Then changed is true
    And the privilege is re-granted without admin option

  @exasol-grants-reject-admin-option-for-object-only-request
  Scenario: Reject admin option for object-only request
    Given an Exasol database is reachable at localhost
    When the grants runtime runs with only object privileges and admin_option true
    Then the runtime fails with a validation error
