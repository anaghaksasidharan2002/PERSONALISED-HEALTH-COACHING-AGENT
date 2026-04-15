def detect_trend(current, previous):

    if previous is None:
        return "No previous data"

    score = 0

    if current["steps"] > previous["steps"]:
        score += 1

    if current["sleep"] > previous["sleep"]:
        score += 1

    if current["exercise"] > previous["exercise"]:
        score += 1

    if score >= 2:
        return "Improving"

    return "Declining"
