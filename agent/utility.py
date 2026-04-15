INPUT_LIMITS = {
    "steps": (0, 100000),
    "sleep": (0.0, 24.0),
    "water": (0, 50),
    "exercise": (0, 720),
}


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def validate_input(data):
    """
    Validate and hard-bound inputs so out-of-range values do not destabilize planning.
    """
    validated = {}
    for key, value in data.items():
        lo, hi = INPUT_LIMITS.get(key, (0, 10**9))
        if value is None:
            validated[key] = lo
            continue
        try:
            numeric = float(value)
        except Exception:
            validated[key] = lo
            continue
        bounded = _clamp(numeric, lo, hi)
        if isinstance(lo, int) and isinstance(hi, int):
            validated[key] = int(round(bounded))
        else:
            validated[key] = float(bounded)
    return validated

def normalize(data):
    normalized = {}
    normalized["steps"] = min(data["steps"] / 10000, 1)
    normalized["sleep"] = min(data["sleep"] / 8, 1)
    normalized["water"] = min(data["water"] / 8, 1)
    normalized["exercise"] = min(data["exercise"] / 30, 1)
    return normalized

def calculate_utility(normalized, weights):
    utility = (
        weights["steps"] * normalized["steps"] +
        weights["sleep"] * normalized["sleep"] +
        weights["water"] * normalized["water"] +
        weights["exercise"] * normalized["exercise"]
    )
    return round(utility, 2)
