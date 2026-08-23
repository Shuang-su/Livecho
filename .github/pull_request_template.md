## Outcome

<!-- What user-visible or engineering outcome does this PR deliver? -->

Closes #

## Accepted artifacts

- Intent: `docs/changes/<issue>-<slug>/intent.md`
- Spec: `docs/changes/<issue>-<slug>/spec.md`
- Plan: `docs/changes/<issue>-<slug>/plan.md`
- Evidence: `docs/changes/<issue>-<slug>/evidence.md`

## Verification

<!-- Paste exact commands and concise results. Do not write only “tests pass”. -->

```text
make verify
```

## Risk and data review

- [ ] No audio was persisted in code, fixtures, logs, databases, queues, or storage.
- [ ] No credentials, cookies, signed stream URLs, model weights, or private exports are
      included.
- [ ] Protocol/schema changes include generated output and compatibility evidence.
- [ ] Raw-event, authentication, and deletion changes include authorization tests.
- [ ] Any implementation deviation is reflected in the accepted artifacts.
- [ ] Rollback or disable path is documented for externally visible behavior.

## Human gate

- [ ] Repository owner reviewed the diff and evidence before merge.
