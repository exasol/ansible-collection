Feature: exasol-info Ansible module runtime specification
  Gather Exasol server information directly through the exasol_info Python
  runtime helpers.

  Background:
    Given an Exasol database is reachable at localhost

  @exasol-info-returns-version-and-cluster-size
  Scenario: Return basic server metadata
    When the info runtime runs with valid login parameters
    Then changed is false
    And version exists and is non-empty
    And database_name exists and is non-empty
    And cluster_size exists and is at least 1

  @exasol-info-uses-qualified-statistical-cluster-metadata-view
  Scenario: Use the qualified statistical cluster metadata view
    Given an Exasol server reports its metadata through SYS.EXA_METADATA
    When the info runtime reads the cluster size
    Then it queries EXA_STATISTICS.EXA_SYSTEM_EVENTS
