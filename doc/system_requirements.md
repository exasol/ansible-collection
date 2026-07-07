# System Requirements

## Introduction

The Exasol Ansible Collection lets operators automate Exasol administration tasks with Ansible modules while relying on Exasol as the authoritative system for authentication and authorization.

## Goals

* Automate Exasol user administration without bypassing Exasol permissions.
* Prevent credentials and passwords from appearing in Ansible output or error messages.
* Make password update behavior explicit where Exasol does not allow password comparison.

## Evidence Base

This draft was reverse-engineered from:

* `doc/user_guide.rst`
* the legacy Exasol user security design note migrated into this document

## Notation

This document uses OpenFastTrace specification items to express product features, user requirements, and acceptance scenarios. Each specification item has a unique identifier in the form `<artifact-type>~<name>~<revision>`.

In this document, feature items use the artifact type `feat`, user requirements use `req`, and acceptance scenarios use `scn`. Design items in `doc/design.md` and `doc/design/` cover the scenarios with artifact type `dsn`. Architecture constraints in `doc/design/constraints.md` use artifact type `constr` and are also covered by `dsn` items.

Informative text explains background, scope, and intent. Specification items define the normative content of the document. Relationships between items are expressed with OpenFastTrace keywords such as `Needs` and `Covers`.

## Terms and Abbreviations

### Exasol Account

An account authenticated by Exasol and authorized according to Exasol's permissions model.

### Secret Value

A password, credential, or authentication token that must not be exposed in task output, logs, or error messages.

## User Roles

### Ansible Operator

An administrator or automation system that runs playbooks using this collection.

## Features

This chapter describes product features at a level suitable for product communication. Detailed user needs and constraints are refined in the requirement items that cover these features.

### Secure Exasol User Administration
`feat~secure-exasol-user-administration~1`

The collection supports Exasol user administration without weakening Exasol authorization or exposing credential material.

Status: draft

Needs: req

## User Requirements

The following requirements refine the product features into user-visible behavior, constraints, and quality expectations.

### Respect Exasol Authorization
`req~respect-exasol-authorization~1`

Collection operations execute with the permissions of the authenticated Exasol account so that existing database authorization rules remain authoritative.

Rationale:

The collection must not provide privilege elevation or grant permissions unavailable to the authenticated Exasol account.

Status: draft

Covers:
- `feat~secure-exasol-user-administration~1`

Needs: scn

### Protect Secret Values
`req~protect-secret-values~1`

Passwords and credentials must be redacted from task output and authentication failures so that secret values are not disclosed through Ansible results.

Rationale:

Ansible output and failure messages may be persisted in logs or CI systems. Secret values must therefore be marked and handled as sensitive data.

Status: draft

Covers:
- `feat~secure-exasol-user-administration~1`

Needs: scn

### Explain Password Update Limits
`req~explain-password-update-limits~1`

Password update behavior must reflect Exasol's inability to return existing passwords so that Ansible Operators can choose between creation-only updates and forced password updates knowingly.

Rationale:

Existing passwords cannot be retrieved or compared. Password update idempotency is therefore intentionally limited by Exasol's security model.

Status: draft

Covers:
- `feat~secure-exasol-user-administration~1`

Needs: scn

## Acceptance Scenarios

The following scenarios describe observable behavior in Given-When-Then form.

### Operation Uses Authenticated Exasol Permissions
`scn~operation-uses-authenticated-exasol-permissions~1`

**Given** an authenticated Exasol account without the required administrative privilege
**When** an Ansible Operator runs a user administration task
**Then** Exasol rejects the operation according to its authorization rules
**And** the collection does not elevate privileges

Status: draft

Covers:
- `req~respect-exasol-authorization~1`

Needs: dsn

### Password Is Not Exposed In Failure Output
`scn~password-not-exposed-in-failure-output~1`

**Given** `login_password` contains a secret value
**When** authentication fails
**Then** the error message must not contain the secret value
**And** the task output must redact the password

Status: draft

Covers:
- `req~protect-secret-values~1`

Needs: dsn

### Creation-Only Password Update
`scn~creation-only-password-update~1`

**Given** `update_password=on_create`
**When** an Ansible Operator manages an existing Exasol user
**Then** the collection does not attempt to update the user's password

Status: draft

Covers:
- `req~explain-password-update-limits~1`

Needs: dsn

### Forced Password Update
`scn~forced-password-update~1`

**Given** `update_password=always`
**When** an Ansible Operator manages an existing Exasol user
**Then** the collection attempts to update the user's password
**And** the result may report `changed=true` even if the provided password matches the existing password

Status: draft

Covers:
- `req~explain-password-update-limits~1`

Needs: dsn

## Open Issues

Record unresolved questions, contradictions, and weakly supported inferences. Do not remove an issue until the user has resolved it or a stronger source has been found.
