# Design

This document describes the architecture of `ansible-collection`.

User perspective, audience, features, user requirements, and acceptance scenarios are defined in [System Requirements](system_requirements.md). This design document focuses on architecture, technical decisions, runtime behavior, and implementation structure.

The structure follows arc42 with the user-perspective parts reduced to short references instead of duplicated content.

## Structure

```{toctree}
:maxdepth: 2
:hidden:

system_requirements
design/constraints
design/context_and_scope
design/solution_strategy
design/building_block_view
design/runtime_view
design/deployment_view
design/crosscutting_concepts
design/security_considerations
design/architecture_decisions
design/quality_requirements
design/risks_and_technical_debt
design/domain/entity_model_relationship
design/domain/use_cases
design/domain/glossary
design/open_issues
```

### Introduction and Goals

This design document explains how the system realizes the requirements defined in [System Requirements](system_requirements.md).

### Architecture Constraints

See [Architecture Constraints](design/constraints.md).

### Context and Scope

See [Context and Scope](design/context_and_scope.md).

### Solution Strategy

See [Solution Strategy](design/solution_strategy.md).

### Building Block View

See [Building Block View](design/building_block_view.md).

### Runtime View

See [Runtime View](design/runtime_view.md).

### Deployment View

See [Deployment View](design/deployment_view.md).

### Crosscutting Concepts

See [Crosscutting Concepts](design/crosscutting_concepts.md).

### Security Considerations

See [Security Considerations](design/security_considerations.md).

### Architecture Decisions

See [Architecture Decisions](design/architecture_decisions.md).

### Quality Requirements

See [Quality Requirements](design/quality_requirements.md).

### Risks and Technical Debt

See [Risks and Technical Debt](design/risks_and_technical_debt.md).

### Domain Model

The entity model, aggregate boundaries, and per-use-case EventStorming
diagrams derived from the Gherkin scenarios in `specs/ansible_modules` and
`specs/ansible_playbook`. See [Entity Model
Relationship](design/domain/entity_model_relationship.md) and the [Use Case
EventStorming Diagrams](design/domain/use_cases.md).

### Glossary

See the [Glossary](design/domain/glossary.md) for terms used across this
design document and the Gherkin acceptance scenarios.

### Open Issues

See [Open Issues](design/open_issues.md).
