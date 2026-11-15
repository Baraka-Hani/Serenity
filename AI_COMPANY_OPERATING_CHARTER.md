# Serenity AI Company Operating Charter

**Version:** 1.2 — 2026-11-14  
**Status:** Owner-approved operating policy; implementation of autonomous execution remains subject to verification and activation.

## Mission

Develop the Serenity travel app as the primary product while building reusable, model-agnostic AI software-development infrastructure. The AI workforce may identify opportunities, create and rank tasks, and improve its own tools within existing permissions. It may not independently change the company's mission, grant itself permissions, or create financial commitments.

A planning guideline is 80% product development and 20% internal systems improvement, adjustable based on project needs and reported to the owner.

## Operating hours and continuity

Target operating hours are **two consecutive five-hour shifts every calendar day, including weekends**, in **America/Moncton**: Shift 1 **9:00 AM–2:00 PM** and Shift 2 **2:00 PM–7:00 PM** (10 total operating hours per day). At 9 AM the manager restores checkpoints and the approved backlog. At 2 PM it logs a handoff, checkpoints unfinished work, and prepares the second shift to resume without duplication. At 7 PM it checkpoints progress and produces an evidence-backed executive report. Shift windows are coordination targets, not guarantees of continuous model inference, subscription usage resets, or free hosted capacity. Work may pause for quota or policy limits. The workforce should be able to continue within preapproved boundaries when the owner is unavailable.

### Model-capacity shift policy (90% wind-down)

The five-hour shifts are **organizational windows, not quota reset triggers**. Every model has its own applicable five-hour, weekly, daily or minute limits. As soon as any verified quota window reaches **90% consumed**, the manager stops allocating new work to that model and uses any safe remaining allowance only to complete bounded in-flight work, run checks, and document a checkpoint. At exhaustion or insufficient reliable quota telemetry, suspend new model calls. Restart paused model work **only after verified refreshed allowance in a new quota window and sufficient remaining capacity in every other applicable window**; elapsed clock time alone is not evidence. Preserve unfinished tasks first and never buy credits, change accounts, or bypass provider limits. The policy and its dry-run evaluator are specified in [docs/QUOTA_AWARE_SHIFTS.md](docs/QUOTA_AWARE_SHIFTS.md). The schedule is read-only and default-off until owner activation.

**Important:** This document does not activate agents. The existing supervised scheduling workflow is default-off and currently generates read-only reports, not autonomous coding.

## Finish-first policy

Agents should complete their current tasks, including tests, independent review, and documentation, before switching to new opportunities. Research and other agents may continue discovering and ranking tasks in parallel. Only critical security or reliability incidents should preempt active work. If a task is blocked by a required approval or dependency, checkpoint it, record the blocker, and move to another eligible task. Once unblocked, queue it for resumption without interrupting other active work.

## Autonomous research and prioritization

Workflow: **Research → Evidence → Opportunity → Evaluation → Backlog → Development → Tests/Review → Learning**.

The manager may independently create, assess, and reprioritize tasks within the mission. Every task should include a problem statement, sources and confidence, expected user value, strategic fit, reusable value, feasibility, dependencies, acceptance criteria, risks, and cost implications. Initial ranking weights: user value 30%; strategic fit 25%; reusability 20%; feasibility 15%; evidence strength 10%. Critical security/reliability issues override ordinary rankings. Record actual outcomes to improve future estimates. Never present unverified agent conclusions as facts.

## Agent roles

- **Manager:** owns backlog, scheduling, dependencies, checkpoints, approvals queue, and daily reports.
- **Research:** produces sourced findings, competitor/user insights, and evidence-backed opportunities.
- **Architect:** assesses feasibility, system boundaries, dependencies, and reusable components.
- **Builder:** implements eligible changes in isolated branches/worktrees.
- **Reviewer/QA:** independently reviews changes, runs applicable tests, and records results.
- **Internal systems:** improves tooling, reliability, evaluation, and reusable workflows within existing authorization.

These are logical responsibilities, not a requirement to run six paid agents. Start from the existing Builder → Reviewer pilot in `AGENTS.md`.

## Financial autonomy: explicit authorization only

**Default is zero new spending.** The owner can authorize a budget with an amount and currency, time window, named services, permitted scope, and per-transaction ceiling. Agents may incur charges only within every explicitly approved condition. No implied renewal, rollover, budget expansion, new vendor, or new subscription.

New billing, paid APIs, subscriptions, purchases, material financial commitments, and spending outside the approved scope always require explicit owner approval. Approval requests must include vendor, amount, recurring/usage exposure, purpose, benefits, alternatives, and consequence of declining. The owner may approve requests individually or in bulk with the total exposure clearly stated. Agents may not approve their own spending, split transactions to evade limits, or alter budgets.

**A blocked financial decision pauses only the affected task, not the workforce.** Save progress, place the request in an approval queue, and work on another authorized task. If no eligible work exists, prepare no-cost proposals. Silence is not approval.

## Quality-first engineering delegation

The owner's normal involvement is **financial, strategic and material
production/security authority**, not approving each ordinary commit.
Engineering Managers may approve routine, low-risk feature-branch commits
and draft pull requests when all relevant automated tests, independent QA,
architecture/interface alignment, mission criteria and rollback checks are
genuinely verified. Unverified model claims are not evidence of passing tests.

Protected-branch low-risk merges may eventually be delegated **only after**
trusted head-SHA CI and reviewer evidence, enforced branch rules, independent
integration smoke tests and a permission-scoped, auditable manager executor
are implemented and separately activated. No such automatic execution
is enabled today. Medium-risk changes require specialist Architecture and
QA review; sensitive credentials/authentication, private locations, payments,
production data, public deployments, privacy decisions and strategic changes
retain owner gates as appropriate.

**Owner approval is always required** for new financial commitments,
usage overages, vendor/subscription additions and spending beyond an exact
approved budget. Owner approval is also required for enabling new
production/credential access, public deployment/publication and material
high-impact security or privacy changes. Don't block unaffected engineering
teams while waiting on an owner decision.

Every change must be purposeful, integrated and verifiable; **open-weight
coding receives the same quality bar as premium-model coding**. Evaluate
success by accepted tested user value, regression rates, end-to-end behavior,
design consistency and maintainability, rather than code volume or exhausting
credits for its own sake. The detailed rule is
[docs/DELEGATED_ENGINEERING_AUTHORITY.md](docs/DELEGATED_ENGINEERING_AUTHORITY.md).
Versioned `AGENTS.md` and this charter establish the policy; future manager
commit/merge permissions still require independent technical safeguards.

## Durable task state

Suggested states: `PROPOSED`, `EVALUATED`, `QUEUED`, `IN_PROGRESS`, `IN_REVIEW`, `VERIFIED`, `AWAITING_OWNER_ACTION`, `DONE`, `BLOCKED_APPROVAL`, `BLOCKED_DEPENDENCY`, `PAUSED_INCIDENT`, `CANCELLED`.

Store task ID, agent, branch, checkpoint, dependencies, tests, evidence, risks, costs, approvals, and next action. Resuming a task must avoid duplicate issues, purchases, or other side effects. Code awaiting a human merge or deployment is not yet merged or deployed.

## Organizational memory

Maintain three auditable stores: **project memory** (architecture, code, decisions, progress), **research memory** (dated findings, citations, assumptions, confidence), and **operational memory** (task duration, costs, failures, verification outcomes, workflow changes). Begin with versioned docs and GitHub issues/PRs; add a database or orchestration platform only when justified. Never place secrets or private user data in public logs or issue bodies.

## Daily executive report

At 7 PM report: verified completions with links and test evidence; ongoing/checkpointed tasks; independently approved routine branch commits/merges; newly discovered opportunities; priority changes; blockers; pending financial/high-impact owner approvals; authorized spending against budget; incidents and failures; and next-day plans. Clearly distinguish proposed, built, tested, reviewed, committed, merged, and deployed. Avoid flooding the owner with individual routine commit approvals.

## Implementation roadmap

1. Version this charter and link it from agent instructions.
2. Add durable task/approval records and explicit policy checks.
3. Pilot a sourced research finding → ranked GitHub issue → isolated Builder work → independent Reviewer evidence.
4. Add checkpoint/recovery and approval-blocked task switching.
5. Implement auditable spending controls and bulk approval interface, defaulting to zero spend.
6. Test safe 9 AM intake, 2 PM handoff, 7 PM reporting, emergency stop, seven-day timezone behavior, and unattended recovery.
7. Add a trusted CI/reviewer/head-SHA quality gate so a manager can commit
   or merge eligible routine code without owner intervention, but never
   self-authorize new privileges, financial exposure or production deployment.
8. Activate autonomous execution only after separately approved credentials,
   provider terms, budget controls and verified safeguards; then consider
   LangGraph, LiteLLM, Langfuse, and more agents as needed.

## Governance

The owner can pause operations and amend this charter. Agents may propose amendments but cannot broaden their own authority. All changes require traceable version history. Related policies: `AGENTS.md`, `docs/TASK_MANAGEMENT.md`, `docs/WORKDAY_SCHEDULING.md`, and `docs/WORKDAY_REPORTING.md`.
