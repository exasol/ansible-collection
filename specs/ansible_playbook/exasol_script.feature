Feature: exasol-script specification
  Execute multi-statement Exasol SQL scripts from Ansible playbooks.

  @exasol-script-execute-simple-multi-statement-script
  Scenario: Execute a simple multi-statement script
    Given an Exasol database is reachable at localhost
    When exasol_script runs a script creating a schema, a table, and a row
    Then changed is true
    And executed_queries preserves the supplied statement order
    And query_result contains the inserted row's id

  @exasol-script-execute-script-body-with-slash-terminator
  Scenario: Execute a script body terminated by a standalone slash line
    Given an Exasol database is reachable at localhost
    When exasol_script runs a CREATE SCRIPT body with embedded semicolons terminated by a standalone "/" line
    Then changed is true
    And executed_queries contains a single CREATE SCRIPT statement
    And the script exists in EXA_ALL_SCRIPTS

  @exasol-script-read-only-script-reports-unchanged
  Scenario: Read-only script reports unchanged
    Given an Exasol database is reachable at localhost
    When exasol_script runs a script containing only SELECT statements
    Then changed is false
    And query_result contains the last statement's selected value

  @exasol-script-failing-statement-blocks-later-statements
  Scenario: Failing statement blocks later statements
    Given an Exasol database is reachable at localhost
    When exasol_script runs a script whose second statement fails
    Then the module fails with an error mentioning the failing statement
    And the schema from the first statement exists in EXA_ALL_SCHEMAS
    And the table from the third statement does not exist in EXA_ALL_TABLES

  @exasol-script-check-mode-read-only-script
  Scenario: Check mode keeps a read-only script on the execution path
    Given an Exasol database is reachable at localhost
    When exasol_script runs a read-only script in check mode
    Then changed is false
    And query_result is not empty

  @exasol-script-check-mode-write-script
  Scenario: Check mode predicts a write script without executing it
    Given an Exasol database is reachable at localhost
    When exasol_script runs a script creating a schema in check mode
    Then changed is true
    And executed_queries equals the whole script as one entry
    And the schema does not exist in EXA_ALL_SCHEMAS

  @exasol-script-sanitize-bad-credentials
  Scenario: Sanitize bad credential errors
    Given an Exasol database is reachable at localhost
    When exasol_script runs with an invalid login password
    Then the module fails with an authentication error
    And the invalid password is not exposed

  @exasol-script-reject-unsupported-bound-arguments
  Scenario: Reject unsupported bound arguments
    Given an Exasol database is reachable at localhost
    When exasol_script runs with a positional_args argument
    Then the module fails with an unsupported parameters error
