# ADR-001: Enterprise Background Processing Platform

## Status
Accepted

## Context
The application needed to transform all synchronous heavy operations into
a resilient distributed asynchronous execution platform. Heavy operations
must never block API requests.

## Decision

We chose Celery as the foundational task queue with Redis as both broker
and result backend. The architecture follows these principles:

1. **Service Abstraction**: Business logic never directly creates Celery tasks.
   All job creation flows through the JobDispatcher service.

2. **Queue Isolation**: 15 dedicated queues prevent any single job type from
   blocking others. Each queue maps to a functional domain (AI, transcript,
   export, etc.).

3. **Priority System**: 6 priority levels (critical, high, normal, low,
   background, system) with Celery's x-max-priority:10.

4. **Idempotency**: Every job carries a unique key derived from
   (tenant, project, type, payload hash). Redis stores the key for 24 hours
   to prevent duplicate submissions.

5. **Rate Limiting**: Token bucket algorithm with per-scope limits
   (global, tenant, user, job type). Redis Lua scripts ensure atomicity.

6. **Failure Recovery**: Periodic recovery cycles detect and re-dispatch
   stuck jobs (worker crash), orphaned tasks (broker restart), and
   unreachable workers.

7. **Multi-Tenancy**: All jobs carry tenant_id, user_id, and workspace_id.
   Queue routing supports tenant-isolated queues.

8. **Observability**: Prometheus + Grafana + Flower + OpenTelemetry +
   Structured logging with correlation IDs.

## Consequences

### Positive
- Heavy operations never block API requests
- Workers scale independently per functional domain
- Zero-downtime deployments via blue-green strategy
- Automatic recovery from worker crashes and broker restarts
- Full audit trail via TaskEventModel
- Idempotency guarantees no duplicate processing

### Negative
- Increased operational complexity (Redis, Celery workers, Beat)
- Distributed debugging is harder than synchronous
- Eventual consistency between job status and actual state

## Alternatives Considered

1. **Apache Kafka + Consumer Groups**: Higher throughput but greater
   operational complexity. Overkill for our job volume.

2. **AWS SQS + Lambda**: Vendor lock-in, cold start latency, 15-minute
   timeout limit unsuitable for AI operations.

3. **Temporal.io**: Excellent workflow engine but introduces significant
   infrastructure requirements (Cassandra/PostgreSQL + custom server).

4. **Plain asyncio Tasks**: No persistence, no retry, no monitoring,
   no worker distribution.

## References
- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Pub/Sub](https://redis.io/docs/interact/pubsub/)
- [Prometheus Metrics](https://prometheus.io/docs/concepts/metric_types/)
