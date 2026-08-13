Feature: exasol-info Ansible module runtime specification
  Gather Exasol server information directly through the exasol_info Python
  runtime helpers.

  Background:
    Given an Exasol database is reachable at localhost

@id:scn~ansible-modules.exasol-info-returns-version-and-cluster-size~1
# Covers: req~exasol-info-module~1
# Needs: itest
Scenario: Return basic server metadata
    Given the connected database account has read access to SYS.EXA_METADATA and EXA_STATISTICS.EXA_SYSTEM_EVENTS
    When the info runtime runs with valid login parameters
    Then changed is false
    And version exists and is non-empty
    And database_name exists and is non-empty
    And cluster_size exists and is at least 1

@id:scn~ansible-modules.exasol-info-uses-qualified-statistical-cluster-metadata-view~1
# Covers: req~exasol-info-module~1
# Needs: itest
Scenario: Use the qualified statistical cluster metadata view
    Given the connected database account has read access to SYS.EXA_METADATA and EXA_STATISTICS.EXA_SYSTEM_EVENTS
    When the info runtime reads the cluster size
    Then it queries EXA_STATISTICS.EXA_SYSTEM_EVENTS
