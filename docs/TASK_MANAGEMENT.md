# GitHub task-management structure

GitHub Issues is the initial work queue and pull requests are the approval
queue. A custom headquarters is deferred until this workflow produces repeated,
measurable pilot results.

## Workflow states

| State | Meaning | Exit evidence |
| --- | --- | --- |
| Backlog | Idea is captured but not approved | Owner chooses it for refinement |
| Ready | Outcome, acceptance criteria and risk are clear | Builder claims task |
| Building | Isolated implementation is underway | Draft PR and Builder evidence |
| Reviewing | Reviewer is checking diff and evidence | Findings or approval recommendation |
| Changes requested | Builder must address concrete findings | Updated evidence and rereview |
| Owner approval | Checks pass and Reviewer recommends approval | Human merge decision |
| Done | Accepted change is merged | Linked PR and final checks |
| Blocked | Exact dependency prevents progress | Owner action or external change |

## Recommended labels

Create these labels when the Stage 2 branch is published:

| Label | Purpose |
| --- | --- |
| `ai-pilot` | Work eligible for the two-agent pilot |
| `status:ready` | Acceptance criteria and boundaries are complete |
| `status:building` | Builder is active |
| `status:review` | Awaiting independent review |
| `status:blocked` | Exact blocker is documented |
| `risk:low` | Isolated, reversible work |
| `risk:medium` | Auth, privacy, persistence or deployment configuration |
| `risk:stop` | Production, secret, billing, purchase or public action |
| `needs:owner` | Requires a human decision or access action |

Labels describe state; they do not authorize an action.

## Task sizing

The first pilots should fit within one supervised day and change one coherent
area. Split a task when it combines product behaviour with deployment, requires
multiple credentials, or cannot be verified with a small acceptance checklist.

## Evidence required on every pull request

- linked issue and acceptance-criteria status;
- exact changed files;
- exact checks run and outcomes;
- checks not run and why;
- privacy/security and cost impact;
- rollback instructions;
- Reviewer findings and recommendation;
- explicit human merge checkbox.

## First pilot selection rubric

Choose a task that is user-visible, reversible, covered by existing tests, costs
nothing, and requires no production credentials. Avoid authentication changes,
payments, public deployment and Firebase Storage for the first pilot.
