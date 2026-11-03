# Package F TRL 5 notes (English)

| Test | Note |
| --- | --- |
| T-19 | Offline bundle `images.manifest.json` has `signed: false` and `status: pending_signing`. Cosign signing of images is pending on main; digests remain placeholders until then. |
| T-05 | Restore uses `pg_dump` / `pg_restore` into a second Postgres cluster data directory on the same VM (not a separate physical node). |
