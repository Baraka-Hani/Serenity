# Serenity AI company — corrected parallel onboarding plan

**Updated 2026-11-14 at 22:36 America/Moncton.** Owner correction:
**Gemini is assigned to company onboarding, not writing travel-app code.**
Both tracks advance the *same company operating roadmap*, independently.

## Overall outcome: safely reduce time-to-market

Serenity's existing main travel application uses a Python stdlib server,
SQLite, HTML/CSS/JS PWA. A separate `nomad-canvas/` React/Vite prototype is
not today's main product. The company wants a safe, low-supervision process
that ships robust changes to the real travel app without making the owner
approve every routine commit. Priority is tested integration and user value,
not consuming every available token.

The company OS exists as **draft, unmerged, not live** stack:
PR [#12](https://github.com/Baraka-Hani/Serenity/pull/12)
→ [#21](https://github.com/Baraka-Hani/Serenity/pull/21)
→ [#23](https://github.com/Baraka-Hani/Serenity/pull/23)
→ [#25](https://github.com/Baraka-Hani/Serenity/pull/25).
PR #25 CI previously passed:
https://github.com/Baraka-Hani/Serenity/actions/runs/43667172013
The branch stack diverges from newer `main`. No autonomous coding or
approved cloud-state writer is enabled. An expiring CI artifact is not a
durable company database.

## Organizational split: NON-OVERLAPPING AND INDEPENDENT

| | **Gemini — Company Onboarding** | **ChatGPT — Company Engineering** |
|---|---|---|
| GitHub issue | [#27](https://github.com/Baraka-Hani/Serenity/issues/27) | [#28](https://github.com/Baraka-Hani/Serenity/issues/28) |
| Working branch | `gemini/company-onboarding-2026-11-14` | `company/parallel-ops-2026-11-14` |
| Base | `main` | `company/module5-durable-quality-operations` |
| Who advances | Owner starts Gemini in supported research/connected environment | ChatGPT continues technical implementation |
| Edits | `docs/onboarding/**` and permitted admin issue/project metadata | `company/**`, relevant `tools/**`, tests, `docs/operations/**`, reviewed CI |
| G1 / C1 | Provider eligibility, official free quotas, model usage and safety | CI, independent QA and isolated sandbox evidence |
| G2 / C2 | GitHub app least privilege, branch rules, budgets and setup approvals | Durable checkpoints, provider quota gate implementation |
| G3 / C3 | Department SOPs, two shift operations, Obsidian HQ onboarding | Manager QA integration, tested company workflow, HQ export |
| G4 / C4 | One-page owner activation checklist and docs-only PR | Technical draft PR, actual CI results and blockers |
| Must not do | Edit product/agent code, credentials, spend, deploy or activate models | Self-authorize secrets/billing, unsafe AI code execution, merge/deploy |

**Neither track waits on the other's next module.** Joint coordination
issue [#29](https://github.com/Baraka-Hani/Serenity/issues/29) reconciles
outputs, and Module 6 [#26](https://github.com/Baraka-Hani/Serenity/issues/26)
remains the first verified manager-led real feature pilot.

## Time schedule (coordination windows, NOT automatic background execution)

Timezone America/Moncton, starting Saturday evening 14 November 2026.

| Time | Gemini independent onboarding | ChatGPT independent engineering |
|---|---|---|
| Sat 22:40–23:20 | G1: verify two free hosted models, eligibility/terms, quota evidence and ChatGPT/Gemini specialist usage | C1: verify current CI, safe sandbox and exact-head QA controls |
| Sat 23:20–Sun 00:10 | G2: GitHub App/Actions permissions, branch rules, zero-spend plan and owner packet | C2: durable state CAS, replay checks, 90% model dispatch tests |
| Sun 00:10–01:00 | G3: departmental operating charter, inter-agent handoffs, Obsidian HQ onboarding | C3: manager quality gate, HQ reporting, CI tests and draft PR |
| Sun 01:00–01:40 | G4: integrated owner activation checklist, docs-only PR, issue #27 handoff | Technical PR, validation and next action report |
| Sun 01:40–08:00 | Only a genuinely active authorized cloud research task or already-triggered CI can keep working | Same; no unattended coding agents currently enabled |
| Sun 08:00–09:00 | Owner reviews verified admin onboarding and provider blockers | Owner reviews technical CI, PRs, HQ and financial/permission gates; issue #29 |

Gemini will not start by itself. An eligible supported Gemini/AI tool session
must actually be opened and given the handoff. Likewise creating issues
does not cause ChatGPT to code while the owner is asleep. ChatGPT
Automations may be able to perform scheduled **status checks**, but
cannot turn consumer subscriptions into autonomous API credits.

## Accurate quota and shift distinction

Daily company shifts are 09:00–14:00 and 14:00–19:00 Atlantic. A shift is
an administrative work window, **not** the provider quota reset time.
Provider meter evidence must cover every active model/request/token window;
stop new tasks at 90% used, checkpoint current work, and resume only on
account-verified reset. Google AI Plus, ChatGPT Plus/Codex and Groq each
have distinct allowances. No overage or paid fallback without approval.

## Gemini handoff in full

[Official Gemini onboarding mandate](https://github.com/Baraka-Hani/Serenity/blob/gemini/company-onboarding-2026-11-14/docs/onboarding/GEMINI_COMPANY_ONBOARDING.md).

The previously created product-coding assignment under
`gemini/travel-journey-2026-11-14` is superseded and must NOT be followed.

## Evidence and owner permissions

At the combined checkpoint, report:
- **G1–G4** verified official/account facts; specific owner actions;
  permissions, free-tier quota and expected costs (only actual facts)
- **C1–C4** exact technical PR/head SHA, real tests and CI, model status,
  state recovery and HQ audit; mark mock vs real explicitly
- **Joint** blockers, branch conflicts, fully trusted end-to-end
  low-risk candidate readiness and zero-new-spend budget
- **Owner** decides only finances, initial credentials/access, production
  changes and high-impact privacy/security; after independently proven
  controls, routine commits may be manager authorized

No agent execution, new billing, GitHub writer, schedules, source merges or
public deployment can be inferred from this plan.
