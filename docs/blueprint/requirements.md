# Requirements Checklist — AI Governance Platform (ISC challenge, sponsor Shared Services Canada)

Source: ISC challenge notice "Artificial Intelligence (AI) decision-making process visibility, traceability and compliance governance" (opened Oct 30 2026, closes Dec 22 2026 14:00 ET, Phase 2 only, TRL 5 to 9 at entry, up to $2,000,000 CAD, up to 20 months, 1-2 contracts expected). Text copy: `challenge_notice.txt`.
Questions to the Contracting Authority (TPSGC.PASIC-APISC.PWGSC@tpsgc-pwgsc.gc.ca) are due no later than 10 calendar days before closing, so by Dec 12 2026. CanadaBuys is the official source if anything differs.

Every later design item, test and proposal answer must point to one or more IDs below.

## A. Essential (mandatory) outcomes — the solution MUST
| ID | Requirement (plain words) | Key words to prove |
|---|---|---|
| EO-01 | Keep registered AI systems continuously aligned with Canadian laws, policies, directives and other governance rules; find the systems a change affects; flag when a reassessment is needed. | continuous alignment, impact detection, reassessment flag |
| EO-02 | Work with enterprise systems, AI/ML platforms and other governance tools, with minimal customization. | interoperability, low-effort integration |
| EO-03 | Exchange governance information (system metadata, ownership, intent, deployment status, funding state, client info, objectives, risk assessments, AIA, compliance findings, audit evidence, monitoring results, approvals, decision records, control requirements / playbooks) through standards-based APIs, connectors and data-exchange formats. | standards-based API, connectors, data exchange |
| EO-04 | Collect, combine (aggregate) and keep governance information up to date across many source systems. | aggregation, sync |
| EO-05 | Use open standards and documented interfaces to avoid lock-in to proprietary technology. | open standards, documented API |
| EO-06 | Restrict, monitor and control admin access, support access and access to governance data, in line with GoC requirements. | access control, monitoring, GoC security |
| EO-07 | Let the organization itself (no vendor help) set data residency, retention, access and deletion policies. | self-service data policy |
| EO-08 | Assess and reassess each registered AI system against its applicable rules; trigger reassessment when rules or frameworks are added, changed, replaced or retired; turn rules into traceable controls; decide whether each control is satisfied; identify non-conformities. | requirement-to-control traceability, non-conformity |
| EO-09 | Let authorized users add, change, version, replace or retire rules and frameworks and apply them to single systems or groups. At minimum, show compliance assessment against: Policy on Service and Digital, Directive on Automated Decision-Making, Algorithmic Impact Assessment, AI Strategy, AI ethics and responsibilities (Guiding Principles). | framework lifecycle; 5 named GoC frameworks |
| EO-10 | Add, change, version, replace and retire rules, controls and assessment criteria; assign them to systems or groups; apply different criteria by intended use, risk profile or rule set. Encouraged: prove extensibility to NIST, ISO and the EU AI Act. | per-system criteria; extensibility |
| EO-11 | Produce human-readable explanations of each assessment and reassessment. Every finding names the requirement, the evidence used, the result and a confidence score or certainty measure. | explainable findings + confidence |
| EO-12 | Collect, link and keep assurance artefacts: control mappings, assessment records, evidence references, approvals, exceptions, attestations, remediation actions, audit histories. Record whether each artefact came from an authorized person (RBAC). | artefact store, provenance, RBAC |
| EO-13 | Give measurable results with five distinct outcomes: met, partially met, not met, not applicable, unable to determine. | 5-state result |
| EO-14 | Let authorized reviewers validate, reject, modify or annotate findings, and keep an audit log of those decisions. | human oversight, audit log |
| EO-15 | Assess and reassess risks from data, models and AI outputs, and feed the results into governance assessments and assurance work. | data/model/output risk |
| EO-16 | Assess data risks and data quality for each system, with baselines and thresholds, and keep a traceable record of issues. | data quality baseline/thresholds/issues |
| EO-17 | Let the organization define, evaluate and reassess risk, performance and quality measures per system, with configurable measures, thresholds and evaluation criteria, and keep a traceable record of results. | configurable metrics |
| EO-18 | Evaluate and monitor AI outputs against criteria fitting the system's intended use and risks: accuracy, quality, fairness, consistency, safety, alignment with operating requirements. | output monitoring |

## B. Additional outcomes — the solution SHOULD (Q1b, 10 points only if ALL are covered)
| ID | Requirement |
|---|---|
| AO-01 | Deploy on-premises, in private cloud and in Canadian-hosted cloud without major architecture change. |
| AO-02 | Bilingual English and French: user interface, documentation, reports and workflows. |
| AO-03 | Multiple organizations / departments / domains on one platform, each with its own policies, controls, reporting and oversight (multi-tenant). |
| AO-04 | Governance reports, alerts and notifications; integration with collaboration, communication and ticketing / case-management systems. |

## C. Phase 2 mandatory criteria (Pass/Fail)
| ID | Question | What passes |
|---|---|---|
| MC-Q1a | Phase 2 scope | In scope; clearly addresses ALL essential outcomes EO-01..EO-18; scientific and technological basis given. |
| MC-Q2 | Proof of feasibility and current TRL | TRL 5-9 stated (drop-down) with: method of research; objectives and analysis of results; data proving feasibility; evidence of the highest validation done; type of environment and by whom (with title). Fails if: evidence insufficient, basic research, TRL 4 or lower, above TRL 9, vague justification, or just paraphrasing the TRL definition. |
| MC-Q3a | Innovation | Meets at least one ISC innovation definition (invention / new technology or process not on the market; significant modification of existing tech for a new setting; improvement in function, cost or performance over state of the art). Fails if incremental or "good engineering" / next release. |
| MC-Q3b | Advance on state of the art (Pass/Fail + 0/5/12/20 points) | Direct comparison with named competitors; measurable improvements. 20 points = two or more significant improvements, or a new benchmark that can define new market spaces. |

## D. Phase 2 point-rated criteria (minimum 65 of 130 total)
| ID | Question | Max points | Notes |
|---|---|---|---|
| PR-Q1b | Additional outcomes | 10 | All 4 AOs needed for 10. |
| PR-Q3b | Advance on state of the art | 20 | Counted with MC-Q3b. |
| PR-Q4 | Science and technology risks + mitigations | 10 | |
| PR-Q5 | Project risks: human resources, financial, project management, intellectual property, material availability, supply chain | 10 | S&T risks do not belong here. |
| PR-Q6 | Project plan table; concurrent milestones; exit TRL drop-down; must fit within 20 months | 20 | |
| PR-Q7 | Implementation team table | 20 | |
| PR-Q8 | Inclusivity (under-represented groups; Indigenous Business Directory gives 20) | 20 | No personal info of individuals. |
| PR-Q9 | Financial controls, tracking, oversight | 10 | |
| PR-Q10 | Commercialization strategy (past record, other funding, past investment) | 10 | |
Total = 130.

## E. TRL 5 evidence rules (from MC-Q2 and ISC TRL definitions)
| ID | Rule |
|---|---|
| TRL-01 | The prototype must be validated in a relevant environment (TRL 5): integrated components tested with realistic supporting elements, not only unit tests in a lab. |
| TRL-02 | Evidence must be dated, reproducible and include data (test results, metrics), not just a description. |
| TRL-03 | Every test needs a pre-stated objective and a measurable pass/fail target. |
| TRL-04 | State the environment type (e.g., realistic simulated GoC enterprise environment) and who ran the tests, with job title. |
| TRL-05 | Show the R&D method and the history of how the solution reached TRL 5 (paper study → lab → integrated prototype → relevant-environment validation). |
| TRL-06 | Avoid claims that look like basic research or like paraphrasing the TRL definition. |

## F. Program facts (constraints)
| ID | Fact |
|---|---|
| PF-01 | Phase 2 only; max $2,000,000 CAD excluding taxes; max 20 months (excluding final report); 1-2 contracts. |
| PF-02 | No travel anticipated. |
| PF-03 | Eligibility: for-profit, incorporated in Canada, ≤499 FTE, R&D in Canada, 50% wages/FTE/executives in Canada rules. |
| PF-04 | Questions by Dec 12 2026 to TPSGC.PASIC-APISC.PWGSC@tpsgc-pwgsc.gc.ca; answers published as amendments on CanadaBuys. |
| PF-05 | Applicant: Tri-Vision AI & Robotics Inc. (Brampton, ON). All code, documents and IP by Arpan Bom. |
