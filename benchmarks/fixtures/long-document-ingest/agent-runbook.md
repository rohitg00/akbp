# AgentMemory production runbook

## Capture hooks
Agents should record tool calls, file edits, commands, and test outcomes as structured observations.

Decision: Hook output should be append-only JSONL so later agents can audit the sequence.

## Compression and recall
Large transcripts should not be injected directly into every future prompt.

Decision: Summaries should preserve decisions, blockers, commands, and test evidence before ranking memories.

## Approval gate
Durable memory writes should start as a dry-run preview and only apply after review.

Decision: Adapters must repeat the same method, path, and params with approved:true after review.
