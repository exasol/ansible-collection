# Acceptance Specifications

This directory contains acceptance specifications derived from the design doc
Acceptance Criteria.

## Specifications

Each specification describes concrete `Given` / `When` / `Then` scenarios.
Every scenario has a stable Scenario ID, declared as the annotation directly
above the scenario.

Each scenario ID must be present in three places:

- Specification Scenario in the `.feature`.
- Playbook Scenario in the corresponding `_playbook.yml`.
- Acceptance Test in the corresponding `test_acceptance_*.py`.

## Scenario Synchronization Contract

A synchronization test,
`test/integration/test_acceptance_scenario_contract.py`, verifies that every
scenario ID exists in all three locations.

This prevents specification drift between:

- Written specifications in `specs` folder
- Executable Acceptance Tests in `test/integration` folder

## Acceptance Test Execution Model

Each `test_acceptance_*.py` test executes exactly one scenario.

For every test:

- The corresponding `*_playbook.yml` is copied.
- The scenario ID is passed to the playbook.
- The playbook uses `when` guards to execute only the matching
  `Given` / `When` / `Then` block.

This creates a direct mapping between specification scenarios and executable
acceptance tests.
