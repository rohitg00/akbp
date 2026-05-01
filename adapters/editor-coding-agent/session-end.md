# Editor Coding Agent Session End

When a user accepts changes:

1. Identify durable knowledge created during the edit.
2. Create dry-run memory proposals.
3. Ask the user to approve or reject the proposals.
4. Apply approved writes only.

Avoid storing raw editor buffers unless the user explicitly requests it.
