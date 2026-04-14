from __future__ import annotations

from database.db import (
    get_learning_state_row,
    update_learning_state_row,
    get_coaching_state,
    update_coaching_state,
    get_user_preferences,
    upsert_user_preference,
)

from agent.preferences import merge_kv_preferences, parse_feedback_to_preferences, preferences_to_kv

def get_learning_state(*, user_id: int = 1):
    row = get_learning_state_row(user_id=user_id)
    # Row shape is backward compatible:
    # - legacy: (steps, sleep, water, exercise, threshold, failure_count, learning_rate)
    # - new:    (steps, sleep, water, exercise, prefer_cardio, threshold, failure_count, learning_rate)
    prefer_cardio = 0.5
    if row is None:
        weights_row = (0.30, 0.30, 0.20, 0.20)
        threshold = 0.75
        failure_count = 0
        learning_rate = 0.08
    else:
        weights_row = row[:4]
        if len(row) >= 8:
            prefer_cardio = row[4] if row[4] is not None else 0.5
            threshold = row[5]
            failure_count = row[6]
            learning_rate = row[7] if row[7] is not None else 0.08
        else:
            threshold = row[4]
            failure_count = row[5]
            learning_rate = row[6] if len(row) > 6 and row[6] is not None else 0.08

    kv_prefs = get_user_preferences(user_id=user_id)
    return {
        "weights": {
            "steps": weights_row[0],
            "sleep": weights_row[1],
            "water": weights_row[2],
            "exercise": weights_row[3]
        },
        "preferences": {
            # numeric preference used for scoring exercise-plan variants
            "prefer_cardio": float(prefer_cardio),
            # free-form learned constraints/preferences applied in planning
            **kv_prefs,
        },
        "threshold": float(threshold),
        "failure_count": int(failure_count),
        "learning_rate": float(learning_rate),
    }

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def _renormalize(weights: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, float(v)) for v in weights.values())
    if total <= 0:
        return {"steps": 0.30, "sleep": 0.30, "water": 0.20, "exercise": 0.20}
    return {k: float(v) / total for k, v in weights.items()}

def update_from_feedback(
    *,
    user_id: int = 1,
    priorities: list[str],
    adherence: int | None,
    rating: int | None,
    feedback_text: str | None,
    context: dict | None = None,
) -> dict:
    """
    Lightweight utility-based learning:
    - If user adheres + rates high => slightly increase weights on the worked priorities, raise goals a bit.
    - If user does not adhere / rates low => reduce aggressiveness: lower goals and shift weight away from priorities that feel too hard.
    """
    state = get_learning_state(user_id=user_id)
    weights = dict(state["weights"])
    threshold = float(state["threshold"])
    failure_count = int(state["failure_count"])
    lr = float(state.get("learning_rate") or 0.08)
    prefer_cardio = float(state.get("preferences", {}).get("prefer_cardio", 0.5))
    existing_prefs = {k: str(v) for k, v in (state.get("preferences") or {}).items() if k != "prefer_cardio"}

    coaching = get_coaching_state(user_id=user_id)
    steps_goal = int(coaching["steps_goal"])
    sleep_goal = float(coaching["sleep_goal"])
    water_goal = int(coaching["water_goal"])
    exercise_goal = int(coaching["exercise_goal"])
    streak = int(coaching["streak"])

    is_positive = (adherence == 1) or (rating is not None and rating >= 4)
    is_negative = (adherence == 0) or (rating is not None and rating <= 2)

    # Update streak / failure count.
    if is_positive:
        streak += 1
        failure_count = max(0, failure_count - 1)
    elif is_negative:
        streak = 0
        failure_count += 1

    # Keyword-based softness: if user says it's "too hard", ease targets.
    text = (feedback_text or "").lower()
    mentions_hard = any(w in text for w in ["hard", "too much", "pain", "injury", "tired", "busy", "impossible"])
    mentions_easy = any(w in text for w in ["easy", "fine", "ok", "manageable", "good", "great"])

    # Preference learning (content): store structured constraints from free-text feedback.
    parsed = parse_feedback_to_preferences(feedback_text)
    new_kv = preferences_to_kv(parsed)
    merged_kv = merge_kv_preferences(existing_prefs, new_kv)
    for k, v in merged_kv.items():
        upsert_user_preference(user_id=user_id, key=k, value=v)

    # Reflect: if the last recommended plan violated learned avoidances and feedback is negative,
    # amplify those avoidances (close the loop between action -> outcome -> learning).
    try:
        plan_meta = (context or {}).get("plan_meta") or {}
        ex_meta = plan_meta.get("exercise") or {}
        last_contains_cardio = bool(ex_meta.get("contains_cardio"))
    except Exception:
        last_contains_cardio = False

    # Numeric cardio preference used for plan variant scoring.
    # If they explicitly negate cardio, drive preference toward 0.
    if any(x in parsed.avoid_activities for x in ["cardio", "running", "jogging", "hiit"]):
        prefer_cardio = _clamp(prefer_cardio - (lr * 2.0), 0.0, 1.0)
    # If they explicitly prefer cardio-related activities, drive preference up.
    if any(x in parsed.prefer_activities for x in ["cardio", "running", "jogging", "cycling"]):
        prefer_cardio = _clamp(prefer_cardio + (lr * 1.5), 0.0, 1.0)

    # Reflection-based correction: if plan included cardio, user responded negatively,
    # and either the new feedback or existing prefs indicate cardio should be avoided,
    # then push prefer_cardio down more and persist cardio into avoid_activities.
    cardio_should_be_avoided = ("cardio" in parsed.avoid_activities)
    if not cardio_should_be_avoided:
        # check existing stored preference list
        import json as _json
        try:
            avoid_existing = set(_json.loads(existing_prefs.get("avoid_activities", "[]") or "[]"))
        except Exception:
            avoid_existing = set()
        cardio_should_be_avoided = "cardio" in avoid_existing

    if is_negative and last_contains_cardio and cardio_should_be_avoided:
        prefer_cardio = _clamp(prefer_cardio - (lr * 2.5), 0.0, 1.0)
        import json as _json
        try:
            avoid_now = set(_json.loads(merged_kv.get("avoid_activities", "[]") or "[]"))
        except Exception:
            avoid_now = set()
        avoid_now.add("cardio")
        merged_kv["avoid_activities"] = _json.dumps(sorted(avoid_now))
        upsert_user_preference(user_id=user_id, key="avoid_activities", value=merged_kv["avoid_activities"])

    # Weight learning.
    for p in priorities:
        key = p.strip().lower()
        if key == "steps":
            metric = "steps"
        elif key == "sleep":
            metric = "sleep"
        elif key == "water":
            metric = "water"
        elif key == "exercise":
            metric = "exercise"
        else:
            continue

        if is_positive and not mentions_hard:
            weights[metric] = float(weights[metric]) + lr
        elif is_negative or mentions_hard:
            weights[metric] = max(0.05, float(weights[metric]) - lr)

    weights = _renormalize(weights)

    # Threshold adapts: if repeated failure, lower threshold slightly so priorities focus on the biggest gaps.
    if failure_count >= 3:
        threshold = _clamp(threshold - 0.03, 0.55, 0.90)
    elif streak >= 5 and mentions_easy:
        threshold = _clamp(threshold + 0.02, 0.55, 0.90)

    # Target learning (aggressiveness).
    if is_positive and not mentions_hard:
        steps_goal = int(_clamp(steps_goal + 250, 4000, 14000))
        exercise_goal = int(_clamp(exercise_goal + 5, 10, 90))
        water_goal = int(_clamp(water_goal + 0, 4, 14))
        sleep_goal = float(_clamp(sleep_goal + 0.0, 6.0, 9.0))
    if is_negative or mentions_hard:
        steps_goal = int(_clamp(steps_goal - 300, 4000, 14000))
        exercise_goal = int(_clamp(exercise_goal - 5, 10, 90))
        water_goal = int(_clamp(water_goal - 0, 4, 14))
        sleep_goal = float(_clamp(sleep_goal - 0.0, 6.0, 9.0))

    update_learning_state_row(
        user_id=user_id,
        steps_weight=weights["steps"],
        sleep_weight=weights["sleep"],
        water_weight=weights["water"],
        exercise_weight=weights["exercise"],
        prefer_cardio=prefer_cardio,
        threshold=threshold,
        failure_count=failure_count,
        learning_rate=lr,
    )
    update_coaching_state(
        user_id=user_id,
        steps_goal=steps_goal,
        sleep_goal=sleep_goal,
        water_goal=water_goal,
        exercise_goal=exercise_goal,
        streak=streak,
    )

    return {
        "weights": weights,
        "preferences": {
            "prefer_cardio": prefer_cardio,
            **merged_kv,
        },
        "threshold": threshold,
        "failure_count": failure_count,
        "learning_rate": lr,
        "coaching": {
            "steps_goal": steps_goal,
            "sleep_goal": sleep_goal,
            "water_goal": water_goal,
            "exercise_goal": exercise_goal,
            "streak": streak,
        },
    }
