---
orphan: true
---

# Clear Exasol Schema Raw-Size Limits

## Goal

Allow `exasol_schema` to reconcile an existing raw-size limit back to no limit
without treating an omitted property as a requested change.

## Scope

In scope:

* use `raw_size_limit: -1` as the explicit clear sentinel
* emit `ALTER SCHEMA ... SET RAW_SIZE_LIMIT = NULL` only when needed
* preserve omission as unmanaged behavior
* document and test clear behavior, including check mode

## Task List

- [x] Update requirements, runtime design, module documentation, and user guide.
- [x] Implement the clear sentinel and idempotent plan.
- [x] Add unit and backend integration coverage.
- [ ] Run backend integration coverage with configured Exasol credentials.
