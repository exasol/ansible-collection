Feature: exasol-query Ansible module runtime specification
  Execute Exasol SQL statements directly through the exasol_query Python
  runtime helpers.

  @exasol-query-execute-write-query-against-backend
  Scenario: Execute a write query against the backend
    Given an Exasol database is reachable at localhost
    When the query runtime executes a CREATE SCHEMA statement
    Then changed is true
    And executed_queries equals the executed CREATE SCHEMA statement
    And the created schema exists in EXA_ALL_SCHEMAS

  @exasol-query-execute-read-query-against-backend
  Scenario: Execute a read-only query against the backend
    Given an Exasol database is reachable at localhost
    When the query runtime executes a read-only SELECT statement
    Then changed is false
    And executed_queries equals the executed SELECT statement
    And query_result contains the selected value

  @exasol-query-check-mode-ignores-read-only-query
  Scenario: Keep read-only queries on the execution path in check mode
    Given an Exasol database is reachable at localhost
    When the query runtime executes a read-only metadata query
    Then changed is false
    And query_result is not empty

  @exasol-query-check-mode-predicts-write-without-execution
  Scenario: Predict a write query without executing it in check mode
    Given an Exasol database is reachable at localhost
    When the query runtime executes a CREATE SCHEMA statement in check mode
    Then changed is true
    And executed_queries equals the planned CREATE SCHEMA statement
    And query_result is empty
    And the created schema does not exist in EXA_ALL_SCHEMAS

  @exasol-query-check-mode-predicts-no-action-for-comment-only-query
  Scenario: Check mode predicts no action for a query with no real statement
    Given an Exasol database is reachable at localhost
    When the query runtime executes a comment-only query in check mode
    Then changed is false
