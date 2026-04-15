"""APScheduler reminder daemon — schedules and fires Telegram reminder messages."""
import os
import sys
import logging
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from kitchen_agent.messaging.telegram_client import send_message
from kitchen_agent.config.settings import TELEGRAM_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(
    jobstores={"default": MemoryJobStore()},
    job_defaults={
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 300,
    },
)

JOBS: dict[int, str] = {}


def reminder_job(reminder_id: int, chat_id: str, title: str, message: str):
    """The job that fires when a reminder is due."""
    try:
        full_msg = f"🔔 *{title}*\n\n{message}"
        send_message(chat_id, full_msg)
        logger.info(f"Reminder {reminder_id} fired for chat {chat_id}")
        
        from kitchen_agent.storage.database import ReminderDB
        ReminderDB().mark_complete(reminder_id)
    except Exception as e:
        logger.error(f"Error firing reminder {reminder_id}: {e}")


class ScheduleRequest(BaseModel):
    reminder_id: int
    chat_id: str
    title: str
    message: str
    scheduled_time: str


app = FastAPI(title="Reminder Daemon")

_scheduler_started = False


def start_scheduler():
    global _scheduler_started
    if not _scheduler_started:
        scheduler.start()
        _scheduler_started = True
        logger.info("APScheduler started")


@app.on_event("startup")
async def startup():
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown(wait=False)


@app.post("/schedule")
async def schedule_reminder(req: ScheduleRequest):
    """Schedule a reminder job."""
    try:
        run_time = datetime.fromisoformat(req.scheduled_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    
    if run_time <= datetime.now():
        reminder_job(req.reminder_id, req.chat_id, req.title, req.message)
        return {"status": "fired_immediately"}
    
    job = scheduler.add_job(
        func=reminder_job,
        trigger="date",
        run_date=run_time,
        args=[req.reminder_id, req.chat_id, req.title, req.message],
        id=str(req.reminder_id),
        replace_existing=True,
    )
    
    JOBS[req.reminder_id] = req.chat_id
    logger.info(f"Scheduled reminder {req.reminder_id} for {run_time}")
    return {"status": "scheduled", "job_id": job.id}


@app.delete("/schedule/{reminder_id}")
async def cancel_reminder(reminder_id: int):
    """Cancel a scheduled reminder."""
    try:
        scheduler.remove_job(str(reminder_id))
        JOBS.pop(reminder_id, None)
        return {"status": "cancelled"}
    except Exception:
        raise HTTPException(status_code=404, detail="Reminder not found")


@app.get("/schedules")
async def list_schedules():
    """List all scheduled reminders."""
    jobs = scheduler.get_jobs()
    return {
        "jobs": [
            {"id": j.id, "next_run_time": str(j.next_run_time)}
            for j in jobs
        ]
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "jobs_count": len(scheduler.get_jobs()),
    }


if __name__ == "__main__":
    port = int(os.getenv("REMINDER_PORT", 8001))
    uvicorn.run("reminder_daemon:app", host="0.0.0.0", port=port, reload=False)
