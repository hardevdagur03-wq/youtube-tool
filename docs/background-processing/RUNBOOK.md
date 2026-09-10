# Operational Runbook — Background Processing Platform

## Quick Reference

- **Broker**: Redis on port 6379
- **Result Backend**: Redis on port 6379
- **Prometheus**: Port 9800
- **Flower Dashboard**: Port 5555
- **Default Worker Concurrency**: 4

## Starting Workers

### Individual Worker Pools
```bash
# AI worker (handles LLM operations)
celery -A background_processing.celery_app worker --loglevel INFO --concurrency 2 --pool prefork --queues ai,high,critical --hostname ai@%h

# Transcript worker
celery -A background_processing.celery_app worker --loglevel INFO --concurrency 4 --pool gevent --queues transcript --hostname transcript@%h

# Export worker
celery -A background_processing.celery_app worker --loglevel INFO --concurrency 2 --pool prefork --queues export,publishing --hostname export@%h

# Notification worker
celery -A background_processing.celery_app worker --loglevel INFO --concurrency 2 --pool threads --queues email,notification --hostname notify@%h

# Maintenance worker
celery -A background_processing.celery_app worker --loglevel INFO --concurrency 1 --pool solo --queues maintenance,background,system,dead_letter --hostname maintenance@%h

# Default worker
celery -A background_processing.celery_app worker --loglevel INFO --concurrency 4 --pool prefork --queues default,low,background --hostname default@%h
```

### Start Beat Scheduler
```bash
celery -A background_processing.celery_app beat --loglevel INFO
```

## Monitoring

### Health Check
```bash
curl http://localhost:8000/api/background/health
```

### Queue Status
```bash
curl http://localhost:8000/api/background/queues
```

### Metrics
```bash
curl http://localhost:8000/api/background/metrics
```

### Flower Dashboard
```
http://localhost:5555
```

### Prometheus
```
http://localhost:9800/metrics
```

## Common Operations

### List All Queues
```bash
celery -A background_processing.celery_app inspect active
celery -A background_processing.celery_app inspect reserved
celery -A background_processing.celery_app inspect scheduled
```

### Purge All Tasks
```bash
celery -A background_processing.celery_app purge -f
```

### Inspect Dead Letter Queue
```bash
curl http://localhost:8000/api/background/dead-letter
```

### Replay Dead Letter Job
```bash
curl -X POST http://localhost:8000/api/background/dead-letter/{job_id}/replay
```

### Cancel a Job
```bash
curl -X POST http://localhost:8000/api/background/jobs/{job_id}/cancel
```

### Retry a Failed Job
```bash
curl -X POST http://localhost:8000/api/background/jobs/{job_id}/retry
```

## Troubleshooting

### Worker Not Processing Tasks
1. Check worker is running: `celery -A background_processing.celery_app inspect ping`
2. Check queue has messages: `celery -A background_processing.celery_app inspect active`
3. Verify Redis connectivity: `redis-cli ping`
4. Check worker logs for errors

### Jobs Stuck in Running Status
1. The FailureRecovery system will automatically reset jobs stuck >15 minutes
2. Manual: `curl -X POST http://localhost:8000/api/background/jobs/{job_id}/retry`
3. Restart the worker pool: stop and start workers

### Dead Letter Queue Growing
1. Investigate root cause via DLQ inspection
2. Replay jobs after fixing the issue
3. Purge entries if they are no longer needed

### Redis Memory Usage
- Redis is configured with LRU eviction
- Result backend auto-expires after 24 hours
- DLQ entries auto-expire after 7 days
- Monitor: `redis-cli info memory`

## Recovery Procedures

### Worker Crash
1. Automatic: FailureRecovery detects stuck jobs every 5 minutes
2. Jobs reset to "pending" status for re-dispatch
3. Restart worker: follow startup commands above

### Redis Restart
1. All running tasks will fail and retry automatically
2. Idempotency keys will be lost (jobs may re-execute)
3. Rate limiter buckets will reset
4. Workers will reconnect automatically

### Complete System Restart
```bash
# Stop all workers
celery -A background_processing.celery_app control shutdown

# Restart Redis (if needed)
# Restart workers
# Restart beat
```

## Performance Tuning

### Worker Concurrency
- AI workers: 2 (LLM calls are I/O bound)
- Transcript workers: 4-8 (gevent for async I/O)
- Export workers: 2-4 (mixed CPU/I/O)
- Notification workers: 2-4 (threads for network calls)

### Redis Memory Limit
```bash
# Set max memory
redis-cli config set maxmemory 1gb
redis-cli config set maxmemory-policy allkeys-lru
```

### Queue Priority
- Default priority: 5 (0 = highest, 10 = lowest)
- Critical operations use priority 0
- Background tasks use priority 10
