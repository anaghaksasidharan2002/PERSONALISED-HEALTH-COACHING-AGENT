from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressSummary:
    verdict: str  # "Normal", "Improving", "Needs attention"
    message: str
    stats: dict


def _avg(xs: list[float]) -> float:
    return sum(xs) / max(1, len(xs))


def summarize_progress(rows: list[dict], *, coaching: dict) -> ProgressSummary:
    """
    Interpret progress in a friendly, practical way.
    Uses last 7 vs previous 7 days (when available) and target attainment.
    """
    if not rows:
        return ProgressSummary(
            verdict="Normal",
            message="No history yet — your first week is just establishing a baseline. That’s normal.",
            stats={},
        )

    # rows expected newest-first in db, but caller may pass either. Normalize to newest-last for windows.
    rs = list(rows)
    # If 'date' exists, assume order can be used as-is from caller; we use slicing only.

    last7 = rs[-7:] if len(rs) >= 7 else rs[:]
    prev7 = rs[-14:-7] if len(rs) >= 14 else []

    def col(name: str, chunk: list[dict]) -> list[float]:
        out: list[float] = []
        for r in chunk:
            v = r.get(name)
            try:
                out.append(float(v))
            except Exception:
                out.append(0.0)
        return out

    last = {
        "steps": _avg(col("steps", last7)),
        "sleep": _avg(col("sleep", last7)),
        "water": _avg(col("water", last7)),
        "exercise": _avg(col("exercise", last7)),
    }
    prev = None
    if prev7:
        prev = {
            "steps": _avg(col("steps", prev7)),
            "sleep": _avg(col("sleep", prev7)),
            "water": _avg(col("water", prev7)),
            "exercise": _avg(col("exercise", prev7)),
        }

    goals = {
        "steps": float(coaching.get("steps_goal") or 8000),
        "sleep": float(coaching.get("sleep_goal") or 7.5),
        "water": float(coaching.get("water_goal") or 8),
        "exercise": float(coaching.get("exercise_goal") or 30),
    }

    # Attainment ratios (0..+)
    ratio = {k: (last[k] / goals[k] if goals[k] > 0 else 0.0) for k in last}
    met = {k: ratio[k] >= 0.85 for k in ratio}
    met_count = sum(1 for v in met.values() if v)
    metric_status = {}
    for k in ["steps", "sleep", "water", "exercise"]:
        if ratio[k] >= 1.0:
            metric_status[k] = "On target"
        elif ratio[k] >= 0.85:
            metric_status[k] = "Near target"
        else:
            metric_status[k] = "Below target"

    improving_signals = 0
    if prev is not None:
        for k in ["steps", "sleep", "water", "exercise"]:
            if last[k] >= prev[k] * 1.05:  # +5% improvement
                improving_signals += 1

    if met_count >= 2 or improving_signals >= 2:
        verdict = "Improving"
        msg = "Your progress looks normal and trending in a good direction — keep consistency over intensity."
    elif met_count == 0 and prev is not None and improving_signals == 0:
        verdict = "Needs attention"
        msg = "Your progress is still normal, but it’s a bit flat right now. Let’s shrink the plan and rebuild consistency."
    else:
        verdict = "Normal"
        msg = "Your progress looks normal. Small ups/downs are expected — focus on steady routines."

    # Daily guardrail: if the latest check-in is clearly very low, override optimistic weekly messaging.
    latest = rs[-1] if rs else {}
    latest_ratio = {}
    for k in ["steps", "sleep", "water", "exercise"]:
        goal = goals.get(k, 0.0)
        try:
            val = float(latest.get(k) or 0.0)
        except Exception:
            val = 0.0
        latest_ratio[k] = (val / goal) if goal > 0 else 0.0
    latest_met = sum(1 for v in latest_ratio.values() if v >= 0.85)
    latest_very_low = sum(1 for v in latest_ratio.values() if v < 0.40)
    if latest_met == 0 and latest_very_low >= 2:
        verdict = "Needs attention"
        msg = "Today’s check-in is well below target in multiple areas. Keep today simple and rebuild consistency tomorrow."

    return ProgressSummary(
        verdict=verdict,
        message=msg,
        stats={
            "last7_avg": last,
            "prev7_avg": prev,
            "goal": goals,
            "attainment_ratio": ratio,
            "metric_status": metric_status,
            "latest_ratio": latest_ratio,
        },
    )

