# Versioned change artifacts

Every implementation begins with a GitHub Issue and a reviewable artifact directory:

```text
docs/changes/<issue>-<slug>/
├── intent.md
├── spec.md
├── plan.md
└── evidence.md
```

- **Intent** records the problem, user outcome, boundaries, owners, and human decision.
- **Spec** makes behavior, interfaces, failure modes, security, and acceptance precise.
- **Plan** gives an implementation order that does not leave product decisions to the
  implementer.
- **Evidence** records exact commands, results, measurements, reviews, and deviations.

Copy `_template`, rename it with the real Issue number and a lowercase kebab-case slug,
and replace every placeholder. The artifact pull request must merge before product code
is written. Issue 1 is the documented repository-bootstrap exception.

Artifacts are durable engineering records. Do not rewrite accepted intent to disguise an
implementation deviation; update the record and make the decision visible.
