"""Backup scheduler — APScheduler-based cron execution for backup tasks."""

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

logger = structlog.get_logger()

# Global scheduler instance
_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={
                "coalesce": True,       # If missed runs, only fire once
                "max_instances": 1,     # Don't overlap same task
                "misfire_grace_time": 3600,  # Allow 1 hour late execution
            },
        )
    return _scheduler


def start_scheduler():
    """Start the scheduler and load all backup tasks with schedules."""
    from .services.backup_service import list_backup_tasks, run_backup

    scheduler = get_scheduler()

    # Load existing backup tasks
    result = list_backup_tasks()
    if result["success"]:
        for task in result["tasks"]:
            schedule = task.get("schedule", "").strip()
            if schedule:
                _add_backup_job(scheduler, task["id"], schedule)

    scheduler.start()
    job_count = len(scheduler.get_jobs())
    logger.info("scheduler_started", jobs_registered=job_count)


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("scheduler_shutdown")
    _scheduler = None


def add_backup_job(task_id: str, cron_expr: str):
    """Add or update a backup job in the scheduler.

    Args:
        task_id: The backup task ID.
        cron_expr: Cron expression (5 fields: min hour day month dow).
    """
    scheduler = get_scheduler()
    job_id = f"backup_{task_id}"

    # Remove existing job if any
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)

    if cron_expr.strip():
        _add_backup_job(scheduler, task_id, cron_expr)
        logger.info("scheduler_job_added", task_id=task_id, cron=cron_expr)
    else:
        logger.info("scheduler_job_removed", task_id=task_id, reason="empty schedule")


def remove_backup_job(task_id: str):
    """Remove a backup job from the scheduler.

    Args:
        task_id: The backup task ID.
    """
    scheduler = get_scheduler()
    job_id = f"backup_{task_id}"
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)
        logger.info("scheduler_job_removed", task_id=task_id)


def get_scheduled_jobs() -> list[dict]:
    """Get all scheduled backup jobs info.

    Returns:
        List of job info dicts with id, next_run_time, cron expression.
    """
    scheduler = get_scheduler()
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "job_id": job.id,
            "task_id": job.id.replace("backup_", ""),
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return jobs


# ─── Internal ─────────────────────────────────────────────────────────────────

def _add_backup_job(scheduler: BackgroundScheduler, task_id: str, cron_expr: str):
    """Internal: parse cron and add job to scheduler."""
    from .services.backup_service import run_backup

    parts = cron_expr.strip().split()
    if len(parts) != 5:
        logger.warning("scheduler_invalid_cron", task_id=task_id, cron=cron_expr)
        return

    minute, hour, day, month, day_of_week = parts

    try:
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        )
    except Exception as e:
        logger.warning("scheduler_trigger_error", task_id=task_id, cron=cron_expr, error=str(e))
        return

    job_id = f"backup_{task_id}"
    scheduler.add_job(
        _execute_backup,
        trigger=trigger,
        id=job_id,
        name=f"Backup task {task_id}",
        args=[task_id],
        replace_existing=True,
    )


def _execute_backup(task_id: str):
    """Callback: execute a backup task (runs in scheduler thread)."""
    from .services.backup_service import run_backup

    logger.info("scheduler_backup_start", task_id=task_id)
    result = run_backup(task_id)

    if result.get("success"):
        logger.info(
            "scheduler_backup_done",
            task_id=task_id,
            duration=result.get("duration_sec"),
            files=result.get("files_transferred"),
        )
    else:
        logger.error(
            "scheduler_backup_failed",
            task_id=task_id,
            error=result.get("error"),
        )
