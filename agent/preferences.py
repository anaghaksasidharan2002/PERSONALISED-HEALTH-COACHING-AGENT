<<<<<<< HEAD
from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedPreferences:
    # Hard constraints (should not be suggested)
    avoid_activities: list[str]
    avoid_foods: list[str]
    # Positive preferences (should be suggested more)
    prefer_activities: list[str]
    prefer_foods: list[str]
    # Other knobs
    time_mode: str | None  # e.g. "short"
    dietary_pattern: str | None  # e.g. "vegetarian", "vegan"
    exercise_mode: str | None  # e.g. "none"


_NEGATION_RE = re.compile(r"\b(no|avoid|exclude|stop|don't|dont|do not|not)\b", re.IGNORECASE)


def _norm_token(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", s.strip().lower()).strip("_")


def _has_negation_near(text: str, keyword: str, window: int = 18) -> bool:
    t = text.lower()
    i = t.find(keyword.lower())
    if i < 0:
        return False
    left = max(0, i - window)
    right = min(len(t), i + len(keyword) + window)
    span = t[left:right]
    return _NEGATION_RE.search(span) is not None


def parse_feedback_to_preferences(text: str | None) -> ParsedPreferences:
    t = (text or "").strip()
    tl = t.lower()

    avoid_activities: list[str] = []
    prefer_activities: list[str] = []
    avoid_foods: list[str] = []
    prefer_foods: list[str] = []
    time_mode: str | None = None
    dietary_pattern: str | None = None
    exercise_mode: str | None = None

    # Exercise opt-out / rest preference
    if any(k in tl for k in ["no exercise", "dont need exercise", "don't need exercise", "do not need exercise", "no workout", "rest day", "skip workout"]):
        exercise_mode = "none"

    # Time preference
    if any(k in tl for k in ["short session", "short sessions", "less time", "busy", "time tight", "quick workout", "10 min", "15 min"]):
        time_mode = "short"

    # Dietary patterns (not a full NLP, but good practical coverage)
    if "vegan" in tl:
        dietary_pattern = "vegan"
    elif any(k in tl for k in ["vegetarian", "veg diet", "no meat"]):
        dietary_pattern = "vegetarian"

    # Activity keywords
    activity_keywords = [
        "cardio",
        "running",
        "jogging",
        "cycling",
        "elliptical",
        "walking",
        "hiit",
        "strength",
        "weights",
        "mobility",
        "stretching",
        "yoga",
    ]
    for kw in activity_keywords:
        if kw in tl:
            if _has_negation_near(tl, kw):
                avoid_activities.append(kw)
            else:
                # If they mention it without negation, treat it as a weak positive signal.
                prefer_activities.append(kw)

    # Food keywords
    food_keywords = [
        "dairy",
        "milk",
        "gluten",
        "bread",
        "sugar",
        "sweet",
        "fried",
        "spicy",
        "coffee",
        "caffeine",
    ]
    for kw in food_keywords:
        if kw in tl:
            if _has_negation_near(tl, kw):
                avoid_foods.append(kw)
            else:
                prefer_foods.append(kw)

    # De-duplicate and normalize
    avoid_activities = sorted({_norm_token(x) for x in avoid_activities if x})
    prefer_activities = sorted({_norm_token(x) for x in prefer_activities if x})
    avoid_foods = sorted({_norm_token(x) for x in avoid_foods if x})
    prefer_foods = sorted({_norm_token(x) for x in prefer_foods if x})

    # If something is avoided, don’t also treat it as preferred.
    prefer_activities = [x for x in prefer_activities if x not in set(avoid_activities)]
    prefer_foods = [x for x in prefer_foods if x not in set(avoid_foods)]

    return ParsedPreferences(
        avoid_activities=avoid_activities,
        avoid_foods=avoid_foods,
        prefer_activities=prefer_activities,
        prefer_foods=prefer_foods,
        time_mode=time_mode,
        dietary_pattern=dietary_pattern,
        exercise_mode=exercise_mode,
    )


def preferences_to_kv(p: ParsedPreferences) -> dict[str, str]:
    """
    Store preferences as string values so SQLite stays simple.
    """
    return {
        "avoid_activities": json.dumps(p.avoid_activities),
        "prefer_activities": json.dumps(p.prefer_activities),
        "avoid_foods": json.dumps(p.avoid_foods),
        "prefer_foods": json.dumps(p.prefer_foods),
        "time_mode": "" if p.time_mode is None else p.time_mode,
        "dietary_pattern": "" if p.dietary_pattern is None else p.dietary_pattern,
        "exercise_mode": "" if p.exercise_mode is None else p.exercise_mode,
    }


def merge_kv_preferences(existing: dict[str, str], updates: dict[str, str]) -> dict[str, str]:
    """
    Merge list-like preferences as sets; override scalar strings if update is non-empty.
    """
    out = dict(existing)
    for k, v in updates.items():
        if k in {"avoid_activities", "prefer_activities", "avoid_foods", "prefer_foods"}:
            try:
                old_list = json.loads(out.get(k, "[]") or "[]")
            except json.JSONDecodeError:
                old_list = []
            try:
                new_list = json.loads(v or "[]")
            except json.JSONDecodeError:
                new_list = []
            merged = sorted({str(x) for x in (old_list or []) + (new_list or []) if str(x).strip()})
            out[k] = json.dumps(merged)
        else:
            if (v or "").strip() != "":
                out[k] = v
    return out

=======
from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedPreferences:
    # Hard constraints (should not be suggested)
    avoid_activities: list[str]
    avoid_foods: list[str]
    # Positive preferences (should be suggested more)
    prefer_activities: list[str]
    prefer_foods: list[str]
    # Other knobs
    time_mode: str | None  # e.g. "short"
    dietary_pattern: str | None  # e.g. "vegetarian", "vegan"
    exercise_mode: str | None  # e.g. "none"


_NEGATION_RE = re.compile(r"\b(no|avoid|exclude|stop|don't|dont|do not|not)\b", re.IGNORECASE)


def _norm_token(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", s.strip().lower()).strip("_")


def _has_negation_near(text: str, keyword: str, window: int = 18) -> bool:
    t = text.lower()
    i = t.find(keyword.lower())
    if i < 0:
        return False
    left = max(0, i - window)
    right = min(len(t), i + len(keyword) + window)
    span = t[left:right]
    return _NEGATION_RE.search(span) is not None


def parse_feedback_to_preferences(text: str | None) -> ParsedPreferences:
    t = (text or "").strip()
    tl = t.lower()

    avoid_activities: list[str] = []
    prefer_activities: list[str] = []
    avoid_foods: list[str] = []
    prefer_foods: list[str] = []
    time_mode: str | None = None
    dietary_pattern: str | None = None
    exercise_mode: str | None = None

    # Exercise opt-out / rest preference
    if any(k in tl for k in ["no exercise", "dont need exercise", "don't need exercise", "do not need exercise", "no workout", "rest day", "skip workout"]):
        exercise_mode = "none"

    # Time preference
    if any(k in tl for k in ["short session", "short sessions", "less time", "busy", "time tight", "quick workout", "10 min", "15 min"]):
        time_mode = "short"

    # Dietary patterns (not a full NLP, but good practical coverage)
    if "vegan" in tl:
        dietary_pattern = "vegan"
    elif any(k in tl for k in ["vegetarian", "veg diet", "no meat"]):
        dietary_pattern = "vegetarian"

    # Activity keywords
    activity_keywords = [
        "cardio",
        "running",
        "jogging",
        "cycling",
        "elliptical",
        "walking",
        "hiit",
        "strength",
        "weights",
        "mobility",
        "stretching",
        "yoga",
    ]
    for kw in activity_keywords:
        if kw in tl:
            if _has_negation_near(tl, kw):
                avoid_activities.append(kw)
            else:
                # If they mention it without negation, treat it as a weak positive signal.
                prefer_activities.append(kw)

    # Food keywords
    food_keywords = [
        "dairy",
        "milk",
        "gluten",
        "bread",
        "sugar",
        "sweet",
        "fried",
        "spicy",
        "coffee",
        "caffeine",
    ]
    for kw in food_keywords:
        if kw in tl:
            if _has_negation_near(tl, kw):
                avoid_foods.append(kw)
            else:
                prefer_foods.append(kw)

    # De-duplicate and normalize
    avoid_activities = sorted({_norm_token(x) for x in avoid_activities if x})
    prefer_activities = sorted({_norm_token(x) for x in prefer_activities if x})
    avoid_foods = sorted({_norm_token(x) for x in avoid_foods if x})
    prefer_foods = sorted({_norm_token(x) for x in prefer_foods if x})

    # If something is avoided, don’t also treat it as preferred.
    prefer_activities = [x for x in prefer_activities if x not in set(avoid_activities)]
    prefer_foods = [x for x in prefer_foods if x not in set(avoid_foods)]

    return ParsedPreferences(
        avoid_activities=avoid_activities,
        avoid_foods=avoid_foods,
        prefer_activities=prefer_activities,
        prefer_foods=prefer_foods,
        time_mode=time_mode,
        dietary_pattern=dietary_pattern,
        exercise_mode=exercise_mode,
    )


def preferences_to_kv(p: ParsedPreferences) -> dict[str, str]:
    """
    Store preferences as string values so SQLite stays simple.
    """
    return {
        "avoid_activities": json.dumps(p.avoid_activities),
        "prefer_activities": json.dumps(p.prefer_activities),
        "avoid_foods": json.dumps(p.avoid_foods),
        "prefer_foods": json.dumps(p.prefer_foods),
        "time_mode": "" if p.time_mode is None else p.time_mode,
        "dietary_pattern": "" if p.dietary_pattern is None else p.dietary_pattern,
        "exercise_mode": "" if p.exercise_mode is None else p.exercise_mode,
    }


def merge_kv_preferences(existing: dict[str, str], updates: dict[str, str]) -> dict[str, str]:
    """
    Merge list-like preferences as sets; override scalar strings if update is non-empty.
    """
    out = dict(existing)
    for k, v in updates.items():
        if k in {"avoid_activities", "prefer_activities", "avoid_foods", "prefer_foods"}:
            try:
                old_list = json.loads(out.get(k, "[]") or "[]")
            except json.JSONDecodeError:
                old_list = []
            try:
                new_list = json.loads(v or "[]")
            except json.JSONDecodeError:
                new_list = []
            merged = sorted({str(x) for x in (old_list or []) + (new_list or []) if str(x).strip()})
            out[k] = json.dumps(merged)
        else:
            if (v or "").strip() != "":
                out[k] = v
    return out

>>>>>>> 1893ef1731c8d043cfbedb2c2aafaf2c2fac35aa
