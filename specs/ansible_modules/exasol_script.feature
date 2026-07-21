Feature: exasol-script Ansible module runtime specification
  Execute multi-statement Exasol SQL scripts directly through the
  exasol_script Python runtime helpers.

  @exasol-script-execute-multi-statement-script-against-backend
  Scenario: Execute a multi-statement script against the backend
    Given an Exasol database is reachable at localhost
    When the script runtime executes a script creating a schema, a table, and a row
    Then changed is true
    And executed_queries equals the individual statements in the script
    And the created schema exists in EXA_ALL_SCHEMAS

  @exasol-script-execute-script-body-terminated-by-slash
  Scenario: Execute a script body terminated by a standalone slash line
    Given an Exasol database is reachable at localhost
    When the script runtime executes a CREATE SCRIPT body containing embedded semicolons terminated by a standalone "/" line
    Then changed is true
    And executed_queries contains a single CREATE SCRIPT statement
    And the created script exists in EXA_ALL_SCRIPTS

  @exasol-script-execute-read-only-script-against-backend
  Scenario: Execute a read-only script against the backend
    Given an Exasol database is reachable at localhost
    When the script runtime executes a script containing only SELECT statements
    Then changed is false
    And query_result contains the last statement's selected value

  @exasol-script-failing-statement-stops-later-statements
  Scenario: Stop execution after a failing statement
    Given an Exasol database is reachable at localhost
    When the script runtime executes a script whose second statement fails
    Then the operation fails with an error mentioning the failing statement
    And the first statement's effect exists in EXA_ALL_SCHEMAS
    And the third statement's effect does not exist in EXA_ALL_TABLES

  @exasol-script-check-mode-ignores-read-only-script
  Scenario: Keep read-only scripts on the execution path in check mode
    Given an Exasol database is reachable at localhost
    When the script runtime executes a read-only script in check mode
    Then changed is false
    And query_result is not empty

  @exasol-script-check-mode-predicts-write-without-execution
  Scenario: Predict a write script without executing it in check mode
    Given an Exasol database is reachable at localhost
    When the script runtime executes a script creating a schema in check mode
    Then changed is true
    And executed_queries equals the whole planned script as one entry
    And query_result is empty
    And the created schema does not exist in EXA_ALL_SCHEMAS

  @exasol-script-semicolon-in-string-literal-does-not-split-statement
  Scenario: A semicolon inside a string literal does not split a statement
    Given an Exasol database is reachable at localhost
    When the script runtime executes a script whose INSERT statement embeds a semicolon inside a string literal
    Then changed is true
    And executed_queries contains exactly two statements
    And query_result contains the value with the embedded semicolon

  @exasol-script-semicolon-in-comment-does-not-split-statement
  Scenario: A semicolon inside a comment does not split a statement
    Given an Exasol database is reachable at localhost
    When the script runtime executes a script whose line comment and block comment each embed a semicolon
    Then changed is false
    And executed_queries contains exactly two statements

  @exasol-script-execute-script-invocation-side-effect
  Scenario: Invoking a created script has a write side effect
    Given an Exasol database is reachable at localhost
    When the script runtime creates an administration script and invokes it with EXECUTE SCRIPT in the same script
    Then changed is true
    And the table created by the invoked script exists in EXA_ALL_TABLES

  @exasol-script-empty-script-executes-nothing
  Scenario: An empty script executes no statements
    Given an Exasol database is reachable at localhost
    When the script runtime executes a script containing only blank lines and a comment
    Then changed is false
    And executed_queries equals an empty list
