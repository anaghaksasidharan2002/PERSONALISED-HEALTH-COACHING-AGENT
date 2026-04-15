from __future__ import annotations


def generate_reminder(*, priorities: list[str], failure_count: int, coaching: dict) -> list[str]:
    reminders: list[str] = []

    if failure_count >= 3:
        reminders.append("Reset week: we’ll shrink goals for 2 days and rebuild consistency.")

    if "Sleep" in priorities:
        reminders.append("Sleep focus: set a bedtime alarm 45 min earlier and dim screens 30 min before bed.")

    if "Water" in priorities:
        reminders.append(f"Hydration: keep a bottle visible — target {coaching.get('water_goal', 8)} glasses today.")

    if "Steps" in priorities:
        reminders.append("Steps: take a 10‑minute walk after your next meal (easy pace).")

    if "Exercise" in priorities:
        reminders.append("Workout: do the first 5 minutes only — once you start, finishing is easier.")

    if not reminders:
        reminders.append("Maintenance day: keep your routines steady and recover well.")

    return reminders
