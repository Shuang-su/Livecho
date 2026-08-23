# Main branch protection

Apply these settings after the first pull request creates the `main` branch:

1. Create a ruleset targeting the default branch.
2. Disallow branch deletion and non-fast-forward updates.
3. Require pull requests and require the `verify` status check.
4. Require all conversations to be resolved and the branch to be current before merge.
5. Block direct pushes, including by repository administrators, except an explicit
   break-glass action that is recorded in an Issue.
6. Do not require an approving review while there is only one maintainer; the owner's
   explicit merge is the human gate. Enable one required approval when a second
   maintainer joins.
7. Allow squash merge and automatically delete merged branches; disable auto-merge for
   production-affecting changes.

Codex review is advisory and does not replace deterministic checks, owner review, or
production approval.
