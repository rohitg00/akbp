# Compaction handoff review

Date: 2026-05-15

Decision: after a context compaction, adapters should retrieve a cited AKBP handoff snapshot before planning.

The handoff snapshot must use absolute dates, include source ids, preserve lifecycle status, and keep next actions behind the normal review gate.

Next action: continue from the current cited snapshot, not from relative-date memory such as "yesterday" or uncited chat residue.
