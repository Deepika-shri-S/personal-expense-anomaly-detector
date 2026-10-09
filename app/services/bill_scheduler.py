import os
import atexit
from flask import Flask
from app.extensions import scheduler
from app.services.bill_service import BillService

_SCHEDULER_INITIALIZED = False


def scheduled_reminder_job(app: Flask):
    """Job executed periodically by APScheduler inside Flask application context."""
    with app.app_context():
        try:
            alerts = BillService.check_and_create_due_reminders()
            if alerts:
                app.logger.info(f"[Scheduler] Generated {len(alerts)} bill reminder alerts.")
        except Exception as e:
            app.logger.error(f"[Scheduler Error] Bill reminder check failed: {e}")


def init_bill_scheduler(app: Flask) -> None:
    """
    Safely initialize and start APScheduler.
    Guards against:
    1. Disabled scheduler in testing/config
    2. Werkzeug reloader double-spawning (WERKZEUG_RUN_MAIN check)
    3. Duplicate scheduler instance startup
    """
    global _SCHEDULER_INITIALIZED

    if not app.config.get("ENABLE_SCHEDULER", True):
        app.logger.info("[Scheduler] Disabled via configuration.")
        return

    # In development mode, Werkzeug runs two processes: parent and reload worker.
    # We only start the scheduler in the actual worker process (WERKZEUG_RUN_MAIN == 'true')
    # or when not running in debug reloader.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    if _SCHEDULER_INITIALIZED or scheduler.running:
        return

    interval_hours = app.config.get("SCHEDULER_INTERVAL_HOURS", 6)

    scheduler.add_job(
        func=scheduled_reminder_job,
        args=[app],
        trigger="interval",
        hours=interval_hours,
        id="bill_due_date_reminders",
        replace_existing=True,
    )

    try:
        scheduler.start()
        _SCHEDULER_INITIALIZED = True
        app.logger.info(f"[Scheduler] APScheduler started successfully. Running every {interval_hours} hours.")
    except Exception as e:
        app.logger.warning(f"[Scheduler] Could not start APScheduler: {e}")

    # Register clean shutdown at exit
    atexit.register(shutdown_bill_scheduler)


def shutdown_bill_scheduler() -> None:
    """Safely shut down the background scheduler."""
    global _SCHEDULER_INITIALIZED
    if scheduler.running:
        try:
            scheduler.shutdown(wait=False)
            _SCHEDULER_INITIALIZED = False
        except Exception:
            pass
