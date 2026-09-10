# Enterprise Background Processing Platform — Architecture

## Overview

The Background Processing Platform is a Celery-based distributed execution engine
designed to handle millions of asynchronous jobs reliably, efficiently, and
fault-tolerantly. It powers all AI pipeline operations, transcript processing,
SEO analysis, exports, publishing, notifications, scheduled jobs, and future
workflows.

## Architecture Diagram

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  API Gateway │────▶│ Job Dispatcher│────▶│ Queue Router │
└─────────────┘     └──────────────┘     └─────────────┘
                          │                      │
                          ▼                      ▼
                   ┌──────────────┐     ┌─────────────┐
                   │ Idempotency  │     │ Rate Limiter│
                   │   Engine     │     │             │
                   └──────────────┘     └─────────────┘
                          │                      │
                          ▼                      ▼
                   ┌─────────────────────────────────────┐
                   │         Celery Broker (Redis)        │
                   └─────────────────────────────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
            ▼                      ▼                      ▼
    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │  AI Workers  │     │ Transcript   │     │  Export      │
    │  (ai, high)  │     │ Workers      │     │  Workers     │
    └──────────────┘     └──────────────┘     └──────────────┘
    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │ Notification │     │ Maintenance  │     │  Analytics   │
    │  Workers     │     │  Workers     │     │  Workers     │
    └──────────────┘     └──────────────┘     └──────────────┘
                          │
                          ▼
                   ┌──────────────┐     ┌─────────────┐
                   │ Result       │     │ Dead Letter │
                   │ Backend      │     │    Queue    │
                   └──────────────┘     └─────────────┘
                          │                      │
                          ▼                      ▼
                   ┌──────────────┐     ┌─────────────┐
                   │  Database    │     │  Redis      │
                   └──────────────┘     └─────────────┘
```

## Queue Topology

The platform uses 15 dedicated queues to prevent any single bottleneck:

| Queue         | Purpose                          | Priority | Workers      |
|---------------|----------------------------------|----------|--------------|
| critical      | System-critical operations        | 0        | AI           |
| high          | High-priority AI/pipeline jobs    | 3        | AI           |
| default       | Standard jobs                     | 5        | Default      |
| low           | Low-priority jobs                 | 8        | Default      |
| background    | Background maintenance            | 10       | Maintenance  |
| system        | System health checks              | 1        | Maintenance  |
| ai            | AI-intensive operations (LLM)     | 3        | AI           |
| transcript    | Transcript processing             | 5        | Transcript   |
| export        | Export operations                 | 5        | Export       |
| publishing    | CMS publishing                    | 3        | Export       |
| email         | Email notifications               | 5        | Notification |
| notification  | Push notifications / webhooks     | 5        | Notification |
| maintenance   | Cleanup, backup, health checks    | 10       | Maintenance  |
| analytics     | Analytics processing              | 8        | Analytics    |
| dead_letter   | Failed job storage                | 0        | Maintenance  |

## Key Components

### Job Dispatcher
Single entry point for all job creation. Handles:
- Idempotency checks (unique job keys)
- Rate limiting (token bucket per scope)
- Queue routing (type/priority/tenant)
- Persistence to database
- Event emission (Redis Pub/Sub)
- Celery task submission

### Queue Router
Maps job types to functional queues with priority overrides and
tenant isolation. Default routing:

| Job Type Pattern | Queue         |
|------------------|---------------|
| pipeline.*       | high / ai     |
| transcript.*     | transcript    |
| ai.*             | ai            |
| export.*         | export        |
| publishing.*     | publishing    |
| email.*          | email         |
| notification.*   | notification  |
| cleanup.*        | maintenance   |
| system.*         | system        |
| analytics.*      | analytics     |
| backup.*         | maintenance   |
| cache.*          | background    |
| embedding.*      | ai            |

### Workflow Engine
Orchestrates multi-job workflows:
- Sequential chains
- Parallel fan-out (groups)
- Fan-in (chords)
- Conditional branching
- Checkpoint-based resume
- Pipeline orchestration (12 stages)

### Idempotency Engine
Prevents duplicate job execution via SHA256-hashed job keys stored in Redis.
Each key is derived from (tenant, project, type, payload hash).
Keys auto-expire after 24 hours.

### Retry Engine
Exponential backoff with jitter:
- Delay = min(base × 2^attempt, backoff_max)
- Jitter = delay × (0.5 + random × 0.5)
- Non-recoverable errors → immediate DLQ
- Max retries configurable per job

### Dead Letter Queue
Redis-backed storage for permanently failed jobs:
- 7-day TTL auto-expiry
- Recovery recommendation engine
- Replay (manual and batch)
- Inspection and export
- Purge support

### Failure Recovery
Automatic detection and recovery:
- Stuck jobs (worker crash) → reset to pending
- Orphaned tasks (broker restart) → re-dispatch
- Periodic recovery cycles (5-minute intervals)
- Comprehensive crash handling

## Database Schema

### background_jobs
Primary job table with full lifecycle tracking:
- uuid, job_type, status, priority, queue
- payload, progress, retry_history
- celery_task_id, worker_id
- error, traceback, tags
- parent_job_id, lock_key
- started_at, finished_at, scheduled_at
- duration_ms, result_data, recoverable

### background_job_executions
Per-attempt execution records:
- job_id, attempt, status
- worker_id, celery_task_id
- started_at, finished_at, duration_ms
- error, traceback, hostname

### background_worker_nodes
Worker registration and health:
- worker_id, hostname, status
- queues, concurrency, pool_type
- cpu_percent, memory_percent
- active_tasks, tasks_processed

### background_queue_metrics
Queue performance snapshots:
- queue_name, length, active, reserved
- failed_total, completed_total
- avg_wait_time_ms, avg_duration_ms
- throughput_per_minute

### background_task_events
Full audit trail:
- job_id, project_id, celery_task_id
- event_type, event_data, worker_id
- timestamp

## Worker Pools

| Pool         | Queues                          | Concurrency | Pool Type | Max Tasks |
|--------------|---------------------------------|-------------|-----------|-----------|
| ai           | ai,high,critical                | 2           | prefork   | 500       |
| transcript   | transcript                      | 4           | gevent    | 1000      |
| export       | export,publishing               | 2           | prefork   | 500       |
| notification | email,notification              | 2           | threads   | 2000      |
| maintenance  | maintenance,background,system   | 1           | solo      | 100       |
| analytics    | analytics,low                   | 1           | prefork   | 500       |
| default      | default,low,background          | 4           | prefork   | 1000      |

## Monitoring

- Prometheus metrics on port 9800
- Grafana dashboards for queue/worker/job metrics
- Flower dashboard for real-time Celery monitoring
- OpenTelemetry tracing with OTLP export
- Structured JSON logging with correlation IDs
- Health checks: DB, Redis, Celery

## Security

- Payload validation (size, depth, type)
- Sensitive data redaction from logs
- Tenant isolation (all jobs carry tenant_id)
- Rate limiting per tenant/user/project/global
- Job type validation (allowlist prefixes)
- Secrets never stored in payloads or logs
