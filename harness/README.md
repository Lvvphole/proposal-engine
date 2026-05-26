# Harness

Operational infrastructure that wraps every agent and pipeline.  These modules are the "nervous system" — they don't contain business logic, but nothing runs without them.

| Module | Responsibility |
|---|---|
| `budget.py` | Token/cost tracking, per-envelope and daily limits |
| `retry.py` | Retry orchestration with backoff and jitter |
| `escalation.py` | Routes failures to recovery agent or human review |
| `handoff.py` | Agent-to-agent handoff protocol with contract checks |
| `audit.py` | Immutable event log for compliance and debugging |
| `instrumentation.py` | Metrics, counters, latency histograms |
| `observability.py` | Structured logging, trace context propagation |
| `quality_judge.py` | Post-extraction quality scoring |
| `sandbox.py` | Isolation boundary for untrusted document processing |
