# Porter Artifact Lifecycle SOP

## Purpose

Porter closes the gap between “generated” and “safely governed.” Every material
mission artifact moves through explicit lifecycle states: generated, validated,
installed, registered, and archived.

## Required record

Record the mission, artifact name, source locator, SHA-256, intended destination,
metadata, creator, and timestamps. Before finalization, verify:

- the destination is the intended canonical or operational location;
- the installed bytes match the registered SHA-256;
- the artifact is registered in the applicable manifest or Source-of-Truth record;
- the archive locator exists and preserves provenance and rollback;
- cleanup does not remove the only registered copy.

Porter records archive and cleanup evidence separately. Source cleanup is
refused if destination or archive evidence is absent or if the source is the
only registered copy. Failed or partial movement preserves the source and emits
a failure record for FIX.

## Production housekeeping

Do not delete releases, backups, audit records, failed artifacts, or source
packages merely because a newer copy exists. Retention requires verified
off-server evidence, approved policy, and a recoverable rollback path.
