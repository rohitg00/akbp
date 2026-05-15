# Inherited repo intake

Use this flow when a coding agent enters an unfamiliar repository and needs
project memory without trusting stale summaries, uncited handoffs, or automatic
durable writes.

Run the executable example from the repository root:

~~~bash
./examples/inherited-repo-intake/run.sh
~~~

The example simulates a repo takeover with issue notes, PR notes, and release
notes. It records those files as source evidence, stores a few reviewed claims,
builds the index, then proves the safe startup path:

1. Generate a read-only `client-config`.
2. Negotiate `akbp.capabilities` with read-only and startup-context profiles.
3. Run `akbp.doctor --profile read-only`.
4. Retrieve cited context through `akbp.session.start`.
5. Reject an unapproved write with `approval_required`.
6. Treat changed source evidence as a review blocker before trusting recalled
   context.

## Rules

- Start with `akbp discover` or an explicit `--path`; do not guess the KB.
- Run `akbp doctor --profile read-only` before planning from recalled context.
- Use `akbp.session.start` with a bounded task and require citations.
- Run `akbp source verify --fail-on-issue` before trusting old inherited-repo
  claims.
- Keep write tools disabled until the host can show dry-run previews and collect
  explicit approval.
- Treat empty, uncited, or source-drifted context as a setup gap, not permission
  to invent repo history.

Expected success markers:

~~~text
AKBP inherited repo intake example
read-only inherited repo startup ok
unapproved inherited repo write blocked ok
cited inherited repo context ok
stale inherited repo evidence requires review ok
stale inherited repo context blocked ok
AKBP inherited repo intake example passed
~~~
