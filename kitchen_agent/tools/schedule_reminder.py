"""schedule_reminder tool — schedules a proactive reminder via APScheduler."""
import requests
from langchain_core.tools import tool
from kitchen_agent.storage.database import ReminderDB
from kitchen_agent.config.settings import REMINDER_DAEMON_URL
from datetime import datetime

_reminder_db = ReminderDB()

@tool
def schedule_reminder(
    title: str,
    message: str,
    scheduled_time: str,
    user_id: str = "default",
    metadata: dict = None,
) -> str:
    """Schedule a proactive reminder to be sent to the user at a specific time.

    This is how the agent becomes proactive — it schedules reminders so you
    don't forget to start marinating, thaw meat, prep ingredients, etc.

    Args:
        title: Short title for the reminder (e.g., "Marinate chicken",
            "Thaw ground beef", "Prep dough").
        message: The full reminder message to send (e.g.,
            "Time to put the chicken in the marinade for tonight's dinner!").
        scheduled_time: When to send the reminder. Format: "YYYY-MM-DD HH:MM"
            (e.g., "2026-04-13 16:00"). Or use relative phrases like
            "in 2 hours", "tomorrow at 9am" in your response text — but
            pass the parsed datetime here.
        user_id: User identifier for routing the reminder.
        metadata: Optional extra data (e.g., {"recipe": "tzatziki chicken"}).

    Returns:
        A confirmation with the reminder details and when it will fire.
    """
    try:
        parsed_time = datetime.fromisoformat(scheduled_time)
    except ValueError:
        return (
            f"Invalid time format: '{scheduled_time}'. "
            "Please use 'YYYY-MM-DD HH:MM' format."
        )

    reminder_id = _reminder_db.add(
        title=title,
        message=message,
        scheduled_time=parsed_time,
        user_id=user_id,
        metadata=metadata,
    )

    try:
        resp = requests.post(
            f"{REMINDER_DAEMON_URL}/schedule",
            json={
                "reminder_id": reminder_id,
                "user_id": user_id,
                "title": title,
                "message": message,
                "scheduled_time": parsed_time.isoformat(),
            },
            timeout=10,
        )
        if resp.status_code != 200:
            pass
    except requests.RequestException:
        pass

    return (
        f"Reminder scheduled: '{title}'\n"
        f"Message: {message}\n"
        f"Will fire at: {parsed_time.strftime('%b %d at %H:%M')}"
    )
