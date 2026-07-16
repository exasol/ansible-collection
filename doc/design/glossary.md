# Glossary

This chapter defines design-specific terms used in the architecture documentation.

General project terms are defined in [System Requirements](../system_requirements.md).

## Desired State

The requested end state of a managed Exasol object. `state=present` means that
the object should exist, while `state=absent` means that the object should not
exist.

## Check-Mode No-Action Prediction

A check-mode result indicating that the current object state already matches the
desired state. The runtime reports `changed=false`, preserves the observed
`exists` value, and reports no state-changing statements in `executed_queries`.
Metadata queries used to observe the current state may still execute.

The equivalent scenarios are:

| Current object state | Desired state | Equivalent scenario wording |
|---|---|---|
| Object exists | `state=present` | Check mode predicts no action when object exists |
| Object does not exist | `state=absent` | Check mode predicts no action when object does not exist |
