# Roadmap

Rough priority order. Each item should become a GitHub issue.

## Reliability
- [ ] Optional Celery / RQ / Django-Q backends to trigger delivery right after commit (`transaction.on_commit`)
- [ ] Per-endpoint circuit breaker (pause an endpoint after repeated failures, auto-resume)
- [ ] Per-endpoint rate limiting and concurrency limits
- [ ] Optional per-endpoint ordering (deliver messages for one key in sequence)
- [ ] Release rows before the HTTP call (claim with a lease) so locks aren't held during network I/O

## Security
- [ ] Block private / loopback / link-local addresses by default (SSRF protection), with an allowlist
- [x] Secret rotation: accept two active secrets per endpoint
- [x] Block private / loopback / link-local addresses by default (SSRF protection), with an allowlist
- [ ] Secret rotation: accept two active secrets per endpoint
- [ ] Encrypt endpoint secrets at rest

## Features
- [ ] Management command to prune delivered messages after N days
- [ ] Payload size limit and validation
- [ ] Admin: payload viewer, filter by event type, bulk replay
- [ ] Metrics hooks (delivered / retried / dead counts, latency) and Prometheus example
- [ ] Async worker using `asyncio` + `httpx` as an optional extra
- [ ] Test client helpers for receivers (`django_outbox.testing`)

## Quality and docs
- [ ] Test against PostgreSQL and MySQL in CI (SKIP LOCKED behaviour)
- [ ] Concurrency test: several workers, no double delivery
- [ ] Documentation site with a recipes section (Stripe-style receiver, idempotency, replay)
- [ ] Publish to PyPI with trusted publishing
- [ ] Type hints throughout and `py.typed`
