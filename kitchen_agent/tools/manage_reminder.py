"""manage_reminder tool — manage reminders (add, list, cancel, complete)."""
import requests
from langchain_core.tools import tool
from datetime import datetime
from kitchen_agent.memory import get_profile
from kitchen_agent.config.settings import REMINDER_DAEMON_URL


@tool
def manage_reminder(
    action: str,
    title: str = None,
    message: str = None,
    scheduled_time: str = None,
    reminder_id: int = None,
    user_id: str = "default",
    metadata: dict = None,
) -> str:
    """Manage reminders — add, list, cancel, or mark complete.

    Actions:
    - "add": Schedule a new reminder.
    - "list": List upcoming reminders.
    - "cancel": Cancel/delete a reminder by ID.
    - "complete": Mark a reminder as done (by ID).

    Args:
        action: What to do — "add", "list", "cancel", "complete".
        title: Short title (e.g., "Marinate chicken"). For add.
        message: Full reminder message. For add.
        scheduled_time: When to fire. Format "YYYY-MM-DD HH:MM". For add.
        reminder_id: Reminder ID. For cancel/complete.
        user_id: User identifier.
        metadata: Extra data. For add.

    Returns:
        A confirmation or list of reminders.
    """
    profile = get_profile(user_id)

    if action == "add":
        if not title or not message or not scheduled_time:
            return "Add requires title, message, and scheduled_time."

        try:
            parsed_time = datetime.fromisoformat(scheduled_time)
        except ValueError:
            return f"Invalid time: '{scheduled_time}'. Use 'YYYY-MM-DD HH:MM'."

        reminder_id = profile.add_reminder(
            title=title,
            message=message,
            scheduled_time=parsed_time,
            metadata=metadata,
        )

        try:
            requests.post(
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
        except requests.RequestException:
            pass

        return (
            f"Reminder scheduled: '{title}'\n"
            f"Message: {message}\n"
            f"Will fire at: {parsed_time.strftime('%b %d at %H:%M')}"
        )

    elif action == "list":
        reminders = profile.retrieve_reminders()
        if not reminders:
            return "No upcoming reminders."
        lines = []
        for r in reminders:
            time_str = r["scheduled_time"][:16].replace("T", " ")
            lines.append(f"- [{r['id']}] {r['title']} at {time_str}")
        return "Upcoming reminders:\n" + "\n".join(lines)

    elif action == "cancel":
        if not reminder_id:
            return "cancel requires reminder_id."
        profile.delete_reminder(reminder_id)
        try:
            requests.delete(
                f"{REMINDER_DAEMON_URL}/schedule/{reminder_id}",
                timeout=10,
            )
        except requests.RequestException:
            pass
        return f"Cancelled reminder {reminder_id}."

    elif action == "complete":
        if not reminder_id:
            return "complete requires reminder_id."
        profile.complete_reminder(reminder_id)
        return f"Marked reminder {reminder_id} as complete."

    else:
        return f"Unknown action: {action}. Use add, list, cancel, complete."