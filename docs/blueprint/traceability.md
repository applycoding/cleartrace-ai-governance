# Traceability — AI Governance Platform (ISC SSC Challenge)

Author: Arpan Bom, Tri-Vision AI & Robotics Inc. Version 1.0, Nov 3, 2026.
Requirement IDs from `requirements.md`. Components (C1–C17) and sections from `BLUEPRINT.md`. Tests from BLUEPRINT section 18 (tier E = essential, R = reduced, D = deferred). Status of every row today: **proposed** (nothing built or tested yet).

## Essential outcomes (must)

| Req | Short | Components | Blueprint sections | Tests | Gap / note |
|---|---|---|---|---|---|
| EO-01 | Continuous alignment; find affected systems; reassessment flags | C5, C6, C3 | 7.2, 7.3 | T-01 (E) | Real policy-change history is limited; captured page set used |
| EO-02 | Interoperability, low effort | C4, C1 | 10.3 | T-02 (E) | Real department systems not available before bid; simulators labelled |
| EO-03 | Exchange 15 information categories in standard formats | C1, C3, C8, C15 | 5.2, 10.1, 10.2 | T-02 (E), T-03 (R) | Funding-state and client-info fields have no standard schema; own JSON Schema |
| EO-04 | Aggregate and keep in sync | C3, C4 | 5.4, 10.3 | T-02 (E), T-04 (R) | — |
| EO-05 | Open standards, no lock-in | C1, C15 | 3.1, 10, 15 | T-03 (R), T-05 (R), T-28 (E) | — |
| EO-06 | Control and monitor admin/support/data access | C2, C12, C17 | 8.2, 8.4, 12.3 | T-06 (E), T-23 (E), T-26 (E), T-29 (R) | JIT approval flow needs a second real identity in tests |
| EO-07 | Self-service residency, retention, access, deletion | C13, C2 | 3.3, 12.1, 12.2 | T-07 (E) | Residency change = controlled migration (not instant) |
| EO-08 | Assess and reassess against applicable rules | C6, C5, C7 | 6, 7.2, 7.5 | T-08 (E), T-13 (E), T-24 (D/R), T-30 (D) | Judgment controls need humans for `met` |
| EO-09 | Manage frameworks; five required GoC packs | C5, C8 | 7.1, 7.4, 7.5, 7.6 | T-01 (E), T-09 (E) | Each pack's clause numbers must be re-read from live text at G0 |
| EO-10 | Configurable controls/criteria per system or group | C5, C6 | 7.1, 7.2, 9.1 | T-10 (E), T-17 (R) | ISO 42001 identifiers only (licensed text) |
| EO-11 | Human-readable explanation with requirement, evidence, result, confidence | C6, C16 | 6.4, 6.5 | T-08 (E), T-11 (R), T-24 (D/R) | Certainty index not called calibrated until T-11 passes |
| EO-12 | Assurance artefacts with authorship and provenance | C9, C12, C2 | 8.1, 8.4 | T-12 (E), T-06 (E), T-23 (E) | — |
| EO-13 | Five outcome states | C6, C15 | 6.2, 10.2 | T-13 (E), T-03 (R) | OSCAL consumers may collapse states; profile + capability check |
| EO-14 | Human review actions with audit log | C10, C12, C16 | 6.3, 8.3, 8.4 | T-14 (E), T-23 (E) | — |
| EO-15 | Data, model, output risk feeds governance | C11, C6 | 9.1, 9.2 | T-15 (E) | — |
| EO-16 | Data quality baselines, thresholds, issue records | C11 | 9.1 | T-16 (R) | Public datasets only |
| EO-17 | Configurable measures and thresholds | C11, C6 | 9.1 | T-17 (R) | Plug-in sandbox scope limited at TRL 5 |
| EO-18 | Output monitoring for accuracy, quality, fairness, consistency, safety, alignment | C11, C7 | 9.1 | T-18 (R) | "Alignment with intended use" partly needs human criteria |

## Additional outcomes (should — all four needed for PR-Q1b points)

| Req | Short | Components | Sections | Tests | Gap / note |
|---|---|---|---|---|---|
| AO-01 | On-prem, private cloud, Canadian cloud | all (packaging) | 3.3, 14 | T-19 (R), T-28 (E) | Two real environments planned; third may be "designed, not run" |
| AO-02 | EN/FR UI, docs, reports, workflows | C14, C16 | 13 | T-20 (R) | Full documentation parity is a contract-period task |
| AO-03 | Multi-tenant, own policies and oversight | C2, all data stores | 12.1 | T-06 (E), T-21 (R), T-29 (R) | — |
| AO-04 | Reports, alerts, collaboration/ticketing integration | C14, C4 | 11 | T-22 (R), T-25 (D) | — |

## Proposal questions

| Req | Covered by | Gap |
|---|---|---|
| MC-Q1a | Sections 2–14 + this file | Narrative still to write |
| MC-Q2 | Sections 1.1, 18; TRL rules below | **No prototype or results yet**; tester name and title needed |
| MC-Q3a | Section 22 | Needs results |
| MC-Q3b / PR-Q3b | Section 22 | Comparative tests need competitor access; wording is "candidate advantage" only |
| PR-Q1b | AO rows above | All four AOs need evidence |
| PR-Q4 | Section 23.1 | — |
| PR-Q5 | Section 23.2, T-26, T-28 | Key-person plan: user input |
| PR-Q6 | Section 17 (pre-bid only) | 20-month plan and budget: user input |
| PR-Q7 | — | User input |
| PR-Q8 | — | User input |
| PR-Q9 | — | User input |
| PR-Q10 | — | User input |

## TRL evidence rules

| Req | How met | Tests |
|---|---|---|
| TRL-01 | Integrated prototype in a realistic simulated GoC environment (section 14, 18) | All E and R tests |
| TRL-02 | Dated, reproducible results with commit and image digests; archived signed artefacts (section 19 step 9) | All |
| TRL-03 | Every test has a pre-stated pass/fail target (section 18) | All |
| TRL-04 | Environment and tester name/title recorded per test | All — tester identity needs user decision |
| TRL-05 | R&D history: research → design blueprint → integrated build → relevant-environment tests | Test report |
| TRL-06 | Plain, specific claims; nothing planned is described as done | Review before submission |

## Program facts

| Req | Note |
|---|---|
| PF-01 | Phase 2, ≤ $2M, ≤ 20 months — plan to be written (user) |
| PF-02 | No travel assumed |
| PF-03 | Eligibility evidence — user |
| PF-04 | Questions by Dec 12 — drafts in BLUEPRINT section 25, send only with approval |
| PF-05 | Applicant and author: Arpan Bom, Tri-Vision AI & Robotics Inc. |

## Test → requirement index

| Test | Tier | Requirements |
|---|---|---|
| T-01 | E | EO-01, EO-09 |
| T-02 | E | EO-02, EO-03, EO-04 |
| T-03 | R | EO-03, EO-05, EO-13 |
| T-04 | R | EO-04 |
| T-05 | R | EO-05 |
| T-06 | E | EO-06, EO-12, AO-03 |
| T-07 | E | EO-07 |
| T-08 | E | EO-08, EO-11 |
| T-09 | E | EO-09 |
| T-10 | E | EO-10 |
| T-11 | R | EO-11 |
| T-12 | E | EO-12 |
| T-13 | E | EO-13, EO-08 |
| T-14 | E | EO-14 |
| T-15 | E | EO-15 |
| T-16 | R | EO-16 |
| T-17 | R | EO-17, EO-10 |
| T-18 | R | EO-18 |
| T-19 | R | AO-01 |
| T-20 | R | AO-02 |
| T-21 | R | AO-03 |
| T-22 | R | AO-04 |
| T-23 | E | EO-06, EO-12, EO-14 |
| T-24 | D/R | EO-08, EO-11 |
| T-25 | D | EO-04, AO-04 |
| T-26 | E | EO-06, PR-Q5 |
| T-27 | D | EO-08..EO-10 |
| T-28 | E | EO-05, AO-01, PR-Q5 |
| T-29 | R | AO-03, EO-06 |
| T-30 | D | EO-08..EO-14 |
