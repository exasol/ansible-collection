Feature: exasol-user specification
  Manage Exasol database users from Ansible playbooks.

  @exasol-user-create-missing-user
  Scenario: Create missing user
    Given an Exasol database is reachable at localhost
    And user "ALICE" does not exist in EXA_ALL_USERS
    When exasol_user runs with:
      | name  | authentication_method | password          | state   |
      | ALICE | password              | Initial_Secret_42 | present |
    Then changed is true
    And user equals "ALICE"
    And exists is true
    And executed_queries equals:
      | sql                                           |
      | CREATE USER "ALICE" IDENTIFIED BY "********" |
      | GRANT CREATE SESSION TO "ALICE"              |
    And user "ALICE" can run query "SELECT 17 AS A" with password "Initial_Secret_42"
    And the module result does not contain "Initial_Secret_42"

  @exasol-user-apply-unchanged
  Scenario: Applying identical user state results in no changes
    Given an Exasol database is reachable at localhost
    And user "ALICE" already exists after exasol_user created it with password "Initial_Secret_42"
    When exasol_user runs again with:
      | name  | authentication_method | password          | state   | update_password |
      | ALICE | password              | Initial_Secret_42 | present | on_create       |
    Then changed is false
    And exists is true
    And executed_queries equals []

  @exasol-user-change-authentication-to-ldap
  Scenario: Change authentication to LDAP
    Given an Exasol database is reachable at localhost
    And user "ALICE" exists with password authentication and password "Initial_Secret_42"
    When exasol_user runs with:
      | name  | authentication_method | ldap_dn                                      |
      | ALICE | ldap                  | cn=alice,dc=authorization,dc=exasol,dc=com |
    Then changed is true
    And exists is true
    And executed_queries equals:
      | sql                                                    |
      | ALTER USER "ALICE" IDENTIFIED AT LDAP AS '********'   |
    And EXA_DBA_USERS.DISTINGUISHED_NAME for "ALICE" equals "cn=alice,dc=authorization,dc=exasol,dc=com"
    And the module result does not contain "cn=alice,dc=authorization,dc=exasol,dc=com"


  @exasol-user-rotate-password
  Scenario: Rotate password
    Given an Exasol database is reachable at localhost
    And user "ALICE" exists with password "Initial_Secret_42"
    When exasol_user runs with:
      | name  | password          | update_password |
      | ALICE | Rotated_Secret_42 | always          |
    Then changed is true
    And exists is true
    And executed_queries equals:
      | sql                                          |
      | ALTER USER "ALICE" IDENTIFIED BY "********" |
    And user "ALICE" can run query "SELECT 19 AS A" with password "Rotated_Secret_42"
    And the module result does not contain "Rotated_Secret_42"
    And the module result does not contain "Initial_Secret_42"

  @exasol-user-check-mode-create
  Scenario: Check mode predicts create
    Given an Exasol database is reachable at localhost
    And user "BOB" does not exist in EXA_ALL_USERS
    When exasol_user runs in check mode with:
      | name | authentication_method | password        | state   |
      | BOB  | password              | Check_Secret_42 | present |
    Then changed is true
    And exists is true
    And executed_queries equals:
      | sql                                         |
      | CREATE USER "BOB" IDENTIFIED BY "********" |
      | GRANT CREATE SESSION TO "BOB"              |
    And user "BOB" still does not exist in EXA_ALL_USERS
    And the module result does not contain "Check_Secret_42"

  @exasol-user-check-mode-update-ldap
  Scenario: Check mode predicts LDAP update
    Given an Exasol database is reachable at localhost
    And user "ALICE" exists with password authentication and password "Initial_Secret_42"
    When exasol_user runs in check mode with:
      | name  | authentication_method | ldap_dn                                            |
      | ALICE | ldap                  | cn=alice-check,dc=authorization,dc=exasol,dc=com |
    Then changed is true
    And exists is true
    And executed_queries equals:
      | sql                                                   |
      | ALTER USER "ALICE" IDENTIFIED AT LDAP AS '********'  |
    And EXA_DBA_USERS.DISTINGUISHED_NAME for "ALICE" remains empty
    And the module result does not contain "cn=alice-check,dc=authorization,dc=exasol,dc=com"

  @exasol-user-check-mode-drop
  Scenario: Check mode predicts drop
    Given an Exasol database is reachable at localhost
    And user "ALICE" exists with password "Initial_Secret_42"
    When exasol_user runs in check mode with:
      | name  | state  | cascade |
      | ALICE | absent | true    |
    Then changed is true
    And exists is false
    And executed_queries equals:
      | sql                       |
      | DROP USER "ALICE" CASCADE |
    And user "ALICE" still exists in EXA_ALL_USERS

  @exasol-user-drop-existing-user
  Scenario: Drop existing user
    Given an Exasol database is reachable at localhost
    And user "ALICE" exists with password "Initial_Secret_42"
    When exasol_user runs with:
      | name  | state  | cascade |
      | ALICE | absent | true    |
    Then changed is true
    And exists is false
    And executed_queries equals:
      | sql                       |
      | DROP USER "ALICE" CASCADE |
    And user "ALICE" no longer exists in EXA_ALL_USERS

  @exasol-user-drop-missing-user
  Scenario: Drop missing user
    Given an Exasol database is reachable at localhost
    And user "ALICE" does not exist in EXA_ALL_USERS
    When exasol_user runs with:
      | name  | state  |
      | ALICE | absent |
    Then changed is false
    And exists is false
    And executed_queries equals []
