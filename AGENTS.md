# AGENTS.md

## Spec-Driven Development

- For issue-driven planning and implementation, use the OpenFastTrace spec-driven development skill:
  https://github.com/itsallcode/openfasttrace/raw/refs/heads/main/.agents/skills/openfasttrace-spec-driven-development/SKILL.md
- Treat `doc/system_requirements.md`, `doc/design_index.md`, referenced `doc/design/` chapters, and `doc/changesets/` as the source of truth for changes that affect requirements, design, behavior, tests, or verification.
- Before substantial implementation for a new issue, create or update the matching changeset in `doc/changesets/` and derive its tasks from the requirements, design, and quality requirements.
- Keep OpenFastTrace IDs stable unless semantics change, and keep traceability clean between requirements, scenarios, threats, design items, implementation, and tests.
- In code and test files, use OpenFastTrace's generated-ID tag form (`[impl -> <target>]`, `[utest -> <target>]`, or `[itest -> <target>]`); do not assign artifact names or versions in the tag.
- Place each trace tag immediately next to the narrowest function or test that implements or verifies the target. Do not put test coverage tags at file level when a specific test provides the evidence.
- Run requirement tracing with `poetry run nox -s requirements:trace`.

## Running Tests

- Check for a local `.env` file before running integration or acceptance tests.
- Define test settings in `.env` with `export`, for example `export PYTEST_ADDOPTS="..."`.
  If `.env` exists, load it for test commands with `source .env; ...` so
  `PYTEST_ADDOPTS` and backend flags are applied.
- For `test/integration/acceptance/*`, a plain `poetry run pytest ...` can be misleading:
  it may skip tests because the backend selection and connection options were not loaded.
- In this repository, the local `.env` currently sets `--backend=onprem` and Exasol connection arguments for acceptance tests.
- If acceptance tests need to connect to a local database or other service, sandboxed execution may fail with socket errors such as `PermissionError: [Errno 1] Operation not permitted`.
- When that happens, rerun the same test command with escalation so the process can reach local services outside the sandbox.
- Distinguish environment failures from code failures:
  skipped tests usually mean missing backend configuration, while connection errors during setup usually mean sandbox/network restrictions.

## Writing Tests

- Prefer one behavior per integration test. Do not mix create, unchanged, update, and drop flows into one lifecycle test when separate tests would keep failures local and obvious.
- For runtime-package integration tests, call the same high-level runtime entry points that the Ansible modules use, such as `run_query()`, `run_user()`, and `run_role()`, so the tests also cover connection creation and wrapper-facing execution flow.
- DB-backed integration tests that use `exasol_login_vars` already get pre-test isolation from `cleanup_exasol_objects_before_test`; do not add normal per-test teardown solely to protect later tests from leftover schemas, users, or roles.
- When verifying resulting database state, do not use the runtime function under test to inspect the result. Open a plain Exasol connection and run direct SQL for verification assertions.
- When an integration test needs pre-existing database state, create that setup data through a normal Exasol connection and direct SQL instead of using the runtime action being tested.
- When expecting an exception in a test, structure the assertion so exactly one invocation can throw; do not combine multiple possibly-throwing calls inside the same exception expectation.
- Keep assertions specific:
  verify both the returned module/runtime result and the observable database side effect where applicable.
- Use `pytest.mark.parametrize` when independent input cases share the same setup and assertion; give cases descriptive IDs so failures identify the affected case directly.
- For query integration coverage, separate read-only and mutating scenarios into different tests, and cover check-mode prediction behavior explicitly when the runtime supports it.

## Formatting Python

- Keep simple function calls on one line when they fit within the formatter's 88-character limit. Use multiline formatting when nested expressions, distinct argument groups, comments, or other complexity make the call materially easier to read. Avoid splitting trivial calls solely for visual symmetry.
