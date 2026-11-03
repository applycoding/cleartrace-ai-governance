# Build rules (read before writing any code)

1. `docs/blueprint/BLUEPRINT.md` is the single source of truth. Build exactly what it says. Deviate only when a pinned version or a test proves it broken, and record why in `docs/adr/`.
2. Clean room: every line of code, rule file, YAML pack and text is written new for this repo. Public projects named in BLUEPRINT section 21 are for ideas and test scenarios only. Never copy their code, rules or text. Datasets only as listed in section 20, with source, licence and attribution in `tests/fixtures/LICENSES.md`.
3. Authorship: every commit's author and committer is `Arpan Bom <arpan-bom@users.noreply.github.com>`. Set `git config user.name "Arpan Bom"` and `git config user.email "arpan-bom@users.noreply.github.com"` before committing. No Co-authored-by trailers. No mention of any coding assistant, AI tool or model vendor in code, comments, docs, commit messages, PR text or file metadata.
4. Shipped licences: permissive only (BLUEPRINT section 15). The licence gate must fail on anything else.
5. Never weaken, skip or fake a test. No `or True`, no `pytest.skip` on required tests, no hard-coded pass results. TRL 5 test results are only recorded from real runs.
6. Plain English in docs, comments and UI text; every user-facing string in both English and French.
7. CI (`.github/workflows/`) runs only on push to `main` and on manual dispatch. Do not add `pull_request` triggers. Run the full test suite on your own machine before pushing.
8. Stay inside the folders your task owns. Change shared contracts (`api/`, `db/`, `services/core-api/` shared modules) only when your task says so, and list any needed contract change in your report instead.
