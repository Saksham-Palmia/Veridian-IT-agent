"""Bounded shared ThreadPoolExecutor for independent blocking I/O operations.

The executor is created once at application startup and reused across all requests.
This avoids the overhead of creating/destroying thread pools per request and provides
a predictable, bounded concurrency limit.

Usage example in the orchestrator:
    from app.core.executor import executor

    future_employee = executor.submit(employee_repo.get, employee_id)
    future_tickets  = executor.submit(itsm_service.get_active_tickets, employee_id)

    employee = future_employee.result()
    tickets  = future_tickets.result()

Three ~50ms SQLite reads run in ~50ms total instead of ~150ms sequentially.
"""

from concurrent.futures import ThreadPoolExecutor

# Bounded to 5 workers — covers the typical max 3 parallel context-fetch operations
# plus headroom for concurrent requests.
executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="veridian-io")

