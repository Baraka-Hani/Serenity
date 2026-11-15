# Serenity AI Company — Onboarding & Governance Suite

Welcome to the **Serenity AI Company Onboarding & Governance Suite**.

This documentation package provides the complete administrative, operational, provider, and security architecture required to onboard and run Serenity's supervised AI workforce under a strict **zero-spend policy** and **least-privilege governance**.

---

## Document Index & Navigation

| Document | Identifier | Scope / Module | Status | Core Focus |
| :--- | :--- | :--- | :--- | :--- |
| [**Mandate Briefing**](GEMINI_COMPANY_ONBOARDING.md) | `DOC-ONB-00` | Track G Mandate | Active Policy | Owner instructions, parallel track charter, hard boundaries (no coding). |
| [**01 — Provider & Quotas**](01_PROVIDER_AND_QUOTAS.md) | `DOC-ONB-01` | Module G1 | Complete | GroqCloud models (`qwen3.8-27b`, `gpt-oss-120b`), rate limits, 90% wind-down, zero-spend setup. |
| [**02 — GitHub & Permissions**](02_GITHUB_AND_PERMISSIONS.md) | `DOC-ONB-02` | Module G2 | Complete | Audited repo settings, branch rulesets, GitHub App architecture, 5 quality gates, Projects board. |
| [**03 — Operations & HQ**](03_COMPANY_OPERATIONS_AND_HQ.md) | `DOC-ONB-03` | Module G3 | Complete | 7 departments, handoff contracts, two-shift runbook (09:00–14:00 / 14:00–19:00), Obsidian HQ, KPIs, incidents. |
| [**04 — Activation & Briefing**](04_ACTIVATION_DECISIONS_AND_HANDOFF.md) | `DOC-ONB-04` | Module G4 | Complete | Master dependency truth table, Sunday morning executive brief, minimum 5 owner activation steps. |

---

## Dual-Track Architecture & Alignment

Serenity's company onboarding roadmap is executed across two independent, non-overlapping workstreams:

```
                               SERENITY ONBOARDING ROADMAP
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
          GEMINI TRACK G (NON-CODING)                  CHATGPT TRACK C (TECHNICAL)
         Associated Issue: #27                         Associated Issue: #28
         Draft PR: #30 (Base: main)                    Draft PR: #31 (Base: PR #25)
         Branch: gemini/company-onboarding-2026-11-14  Branch: company/parallel-ops-2026-11-14
         Deliverable: docs/onboarding/**               Deliverable: company/** & tests
                     │                                             │
                     └──────────────────────┬──────────────────────┘
                                            ▼
                                  JOINT INTEGRATION (#29)
                                  Reconciled Readiness,
                                  Passing CI (#43670053964),
                                  Owner Activation Gate
```

---

## Core Operational Principles

1. **Zero New Spending:** Default is $0.00. No paid APIs, no automatic tier upgrades, no overage charges, and no billing details added without explicit, written owner consent.
2. **Quality Over Token Burn:** Success is measured by verified user value, robust test coverage, and regression prevention—never raw prompt volume or token burn.
3. **Fail-Closed Quotas:** When any model reaches 90% consumption of any applicable rate-limit bucket, new work is immediately suspended. A task resumes only upon authentic, verified provider reset.
4. **Owner Authority Boundaries:** Routine low-risk feature commits may be delegated to the Engineering Manager after passing all automated CI and independent review gates. Financial commitments, credentials, public deployments, production data, and default branch rules require direct owner authorization.
