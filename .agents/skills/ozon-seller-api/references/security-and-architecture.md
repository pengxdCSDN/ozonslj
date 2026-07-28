# Security and architecture

## Preferred boundary

Use this flow for authenticated operations:

`Extension UI/content script -> extension service worker -> application backend -> Ozon Seller API`

The backend owns Ozon credentials, policy checks, rate limiting, audit events, and normalized responses. The extension receives only the data needed for its current view.

## Extension rules

- Keep content scripts untrusted and minimally privileged.
- Validate every message crossing page, content-script, service-worker, and backend boundaries.
- Restrict allowed message types, origins, sellers, identifiers, and payload sizes.
- Do not expose secrets through DOM attributes, injected scripts, browser storage, source maps, console output, or error messages.
- Do not allow arbitrary endpoint paths or arbitrary request bodies from the page.
- Use a fixed allowlist of backend operations.

## Backend rules

- Store seller credentials in a secret manager or encrypted credential store.
- Separate tenants and seller accounts at authorization and storage boundaries.
- Authenticate the extension user independently of Ozon credentials.
- Authorize every operation against the selected seller account.
- Redact headers and sensitive fields before logging.
- Record an audit event for consequential writes without recording secrets.

## Mutation policy

Require an explicit preview and confirmation for price or stock updates, order/posting transitions, cancellations, archival, shipment/document operations, outbound messages, and bulk changes.

Include target identifiers, before/after values when available, total affected count, and a partial-failure recovery plan.
