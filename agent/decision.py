from __future__ import annotations


def find_priority(data: dict, *, coaching: dict, threshold: float = 0.75) -> list[str]:
    """
    Returns a priority list based on gaps vs personalized targets.
    threshold: how far below target we consider it "needs focus".
    """
    priorities: list[str] = []

    steps_goal = int(coaching.get("steps_goal", 8000))
    sleep_goal = float(coaching.get("sleep_goal", 7.5))
    water_goal = int(coaching.get("water_goal", 8))
    exercise_goal = int(coaching.get("exercise_goal", 30))

    if float(data.get("sleep", 0)) < sleep_goal * threshold:
        priorities.append("Sleep")
    if int(data.get("steps", 0)) < int(steps_goal * threshold):
        priorities.append("Steps")
    if int(data.get("water", 0)) < int(water_goal * threshold):
        priorities.append("Water")
    if int(data.get("exercise", 0)) < int(exercise_goal * threshold):
        priorities.append("Exercise")

    return priorities
