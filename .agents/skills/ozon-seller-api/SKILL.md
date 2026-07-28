---
name: ozon-seller-api
description: Design, implement, review, and test safe Ozon Seller API integrations for the ozonslj browser-extension project. Use for Ozon products, prices, inventory, orders, FBO/FBS postings, logistics, reports, finance, chat, analytics, authentication, pagination, retries, rate limits, TypeScript clients, mocks, or API-backed UI flows.
---

# Ozon Seller API

Build Ozon integrations from current official documentation, with credentials isolated from browser-delivered code and destructive operations guarded.

## Workflow

1. Classify the requested operation as read-only, reversible write, or destructive write.
2. Consult the current Ozon Seller API documentation before selecting an endpoint or schema. Read [references/official-sources.md](references/official-sources.md).
3. Inspect the project's existing architecture, types, API client, storage, and test conventions.
4. Decide whether the request can safely run in the extension or requires a backend proxy. Follow [references/security-and-architecture.md](references/security-and-architecture.md).
5. Define typed request, response, and normalized domain models. Keep Ozon wire types separate from UI/domain types.
6. Implement the smallest endpoint-specific client method. Centralize authentication, transport, retries, pagination, timeouts, and error mapping.
7. Add mocked contract tests and failure-path tests. Add end-to-end coverage only where it provides additional confidence.
8. Re-check the live documentation for version, deprecation, limits, and required headers before declaring completion.

## Non-negotiable safeguards

- Never embed `Api-Key`, `Client-Id`, refresh tokens, or seller credentials in extension source, bundles, logs, screenshots, fixtures, URLs, or analytics.
- Never obtain credentials by scraping Ozon pages or reading unrelated page/session storage.
- Prefer a backend proxy for authenticated Seller API calls. Give the extension only a short-lived, scoped application session.
- Use least-privilege extension permissions and explicit host permissions.
- Treat price changes, stock changes, shipment transitions, cancellations, archiving, document signing, chat sends, and bulk mutations as consequential writes.
- For consequential writes, show the exact target count and intended change, require explicit user confirmation, and use idempotency or duplicate suppression when available.
- Default bulk tools to preview/dry-run mode. Put bounded concurrency and per-seller rate limits around execution.
- Do not invent endpoint paths, request fields, enum values, quotas, or deprecation dates. Mark unknowns and verify them.

## Client design

- Use `https://api-seller.ozon.ru` only from the trusted service layer unless current official documentation specifies otherwise.
- Send `Client-Id` and `Api-Key` only from server-side secret storage.
- Centralize request IDs, error mapping, timeouts, cancellation, retry policy, pagination, and redacted observability.
- Apply exponential backoff with jitter to retryable failures and honor `Retry-After` when supplied.
- Retry only idempotent reads by default. Retry writes only when endpoint semantics and duplicate protection are understood.
- Preserve raw Ozon identifiers as strings unless the official contract guarantees safe numeric handling.
- Validate external responses at runtime before mapping them into domain models.

## Testing gates

- Mock success, authentication failure, validation failure, throttling, timeout, partial failure, and malformed responses.
- Assert that logs and telemetry redact all credentials and sensitive seller/customer data.
- Test pagination boundaries, empty results, duplicate events, and clock/date-zone behavior.
- For mutations, test preview, confirmation, cancellation, partial completion, and safe retry behavior.
- Use the project `playwright` skill for extension UI flows and `security-best-practices` for security review.

## Completion report

State the verified endpoint version and documentation URL, operation risk class, credential boundary, retry/pagination behavior, tests added, and any unverified assumptions.
