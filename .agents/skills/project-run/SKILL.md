---
name: project-run
description: Reconstruct context, plan, implement, verify, document, and hand off work in the ozonslj repository. Use when starting, resuming, running, debugging, or completing project-development tasks in this repository, especially when work spans the FastAPI backend, React/Chrome-extension frontend, SQLite schema, Ozon Seller API integration, project documentation, ADRs, tests, troubleshooting, or a session handoff.
---

# Project Run

Run ozonslj work from repository evidence through a verified handoff.

## Reconstruct context

1. Confirm the workspace root and inspect `git status --short`. Preserve unrelated user changes.
2. Read only the context relevant to the task:
   - Domain language: `CONTEXT.md`
   - Requirements and scope: `docs/REQUIREMENTS.md`, `docs/PROJECT_PLAN.md`
   - Architecture and contracts: `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/DATABASE.md`
   - Local commands and standards: `docs/LOCAL_DEVELOPMENT.md`, `docs/DEVELOPMENT_STANDARDS.md`
   - Durable agent rules: the nearest `AGENTS.md`, when present
   - Prior incidents: `docs/troubleshooting.md`, when diagnosing tooling or runtime failures
3. Inspect the implementation and tests that own the requested behavior. Do not infer current behavior from documentation alone.
4. State assumptions only when repository evidence cannot resolve them.

## Plan and implement

1. Translate the request into observable outcomes and choose the smallest coherent change.
2. Follow the repository vocabulary in `CONTEXT.md`.
3. Keep boundaries intact:
   - FastAPI routes handle HTTP concerns and dependency injection.
   - Domain modules own business rules and ports.
   - Infrastructure modules own SQLite, encryption, and Ozon transport details.
   - React components consume centralized API types and represent loading, success, empty, error, and retry states.
4. Add or update tests for changed behavior. For a defect, reproduce it with a regression test when practical.
5. Never call a real Ozon account from automated tests. Use stubs or mocks.
6. Preserve credentials, customer data, local databases, `.env` files, and unrelated worktree changes.

## Classify knowledge

Put each lesson in its durable home:

| Knowledge | Destination |
|---|---|
| Repository-wide instruction agents must always follow | `AGENTS.md` |
| Architecture, API, database, setup, or workflow explanation | Matching file under `docs/` |
| Significant technical choice and its tradeoffs | `docs/decisions/` ADR |
| Repeated failure with symptoms, cause, and recovery | `docs/troubleshooting.md` |
| Behavior that must never regress | Automated test |
| Temporary progress, blockers, and next actions | Session handoff |

Do not duplicate the same rule across several destinations. Update an existing document before creating another one.

## Verify proportionally

Run focused checks first, then the repository gate when the change warrants it:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

For frontend-only work, run commands separately so a hung tool is easy to identify:

```powershell
.\extension\node_modules\.bin\tsc.CMD -b extension\tsconfig.json --pretty false
Set-Location extension
.\node_modules\.bin\vite.CMD build --configLoader runner --outDir ..\verify-dist --emptyOutDir false
```

Use a bounded timeout for each external command. If pnpm requests an interactive modules purge, set `CI=true` or use the already-installed project binaries; do not repeatedly launch the same command. If Vite cannot clear `extension/dist`, build to a verified temporary directory inside the workspace and remove only that exact directory afterward.

Report which checks passed, failed, or were skipped. Never claim verification from a command that timed out or was terminated.

## Finish or hand off

1. Review `git diff --check` and the scoped diff.
2. Confirm documentation, schema, API contracts, tests, and implementation agree.
3. Summarize the outcome, important files, verification, and remaining risks.
4. If work must pause, create a handoff containing the goal, completed work, current state, exact blockers, next steps, relevant paths, and commands already attempted. Keep temporary state out of durable repository guidance.
