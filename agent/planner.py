from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlanOutput:
    headline: str
    details: str
    meta: dict = field(default_factory=dict)


def _join_lines(lines: list[str]) -> str:
    return "\n".join(lines).strip() + "\n"


def generate_exercise_plan(*, priorities: list[str], profile: dict, coaching: dict, today: dict, preferences: dict | None = None) -> PlanOutput:
    """
    Returns a detailed, coach-like plan for the next 7 days.
    Safe defaults, personalized via profile/equipment/injuries/schedule.
    """
    goal = (profile.get("goal") or "general_fitness").lower()
    injuries = (profile.get("injuries") or "").lower()
    equipment = (profile.get("equipment") or "").lower()
    schedule = (profile.get("schedule") or "").lower()
    preferences = preferences or {}
    avoid_activities_raw = preferences.get("avoid_activities") or "[]"
    exercise_mode = (preferences.get("exercise_mode") or "").strip().lower()
    try:
        import json as _json
        avoid_activities = set(_json.loads(avoid_activities_raw))
    except Exception:
        avoid_activities = set()

    steps_goal = int(coaching["steps_goal"])
    exercise_goal = int(coaching["exercise_goal"])

    low_impact = any(w in injuries for w in ["knee", "back", "ankle", "pain", "injury"])
    has_gym = any(w in equipment for w in ["gym", "dumbbell", "barbell", "machine"])
    has_band = "band" in equipment
    time_tight = any(w in schedule for w in ["busy", "tight", "shift", "long hours"])

    headline = "Your 7‑day exercise plan (customized)"
    lines: list[str] = []
    lines.append("## Principles (how we’ll win this week)")
    lines.append(f"- **Daily movement target**: aim for **{steps_goal:,} steps/day** (we’ll build up gradually).")
    lines.append(f"- **Workout target**: **{exercise_goal} min/day** on training days, scaled to your schedule.")
    if low_impact:
        lines.append("- **Low‑impact focus**: protect joints; prefer cycling/elliptical/walking + controlled strength work.")
    if time_tight:
        lines.append("- **Time‑tight mode**: we’ll use short sessions with high consistency (10–25 min blocks).")

    lines.append("\n## Today (do this next)")
    if exercise_mode == "none":
        lines.append("- **Rest day (as requested)**: no structured workout today.")
        lines.append("- **Recovery (10–15 min)**: gentle mobility + easy walk for circulation if comfortable.")
        lines.append("- **Minimum viable win**: 5 minutes of stretching or a short walk.")
    elif "Steps" in priorities or "Exercise" in priorities:
        lines.append("- **10‑minute walk** now or after a meal (easy pace).")
        lines.append("- **Mobility (5 min)**: neck rolls, shoulder circles, hip openers, calf stretch.")
        lines.append("- **Strength (10–15 min)**: 2 rounds")
        lines.append("  - Squat to chair x 8–12 (or wall sit 20–40s)")
        lines.append("  - Incline push‑ups x 6–12")
        lines.append("  - Glute bridge x 10–15")
        lines.append("  - Dead bug x 6/side")
    else:
        lines.append("- Keep your routine. Add a **5–10 min walk** after one meal for recovery and steps.")

    lines.append("\n## 7‑day schedule (detailed)")
    if exercise_mode == "none":
        lines.append("- **This week’s emphasis**: recovery + gentle movement (no structured workouts per your preference).")
        week = [
            ["**Day 1 — Recovery**", "- 15–30 min easy walking (or equivalent) + gentle mobility."],
            ["**Day 2 — Recovery**", "- 10–20 min mobility + light stretching."],
            ["**Day 3 — Recovery**", "- Easy walk + optional core (very light)."],
            ["**Day 4 — Recovery**", "- Rest + short walk if you want."],
            ["**Day 5 — Recovery**", "- Mobility + posture work."],
            ["**Day 6 — Recovery**", "- Easy walk + stretch."],
            ["**Day 7 — Optional**", "- Gentle activity you enjoy; keep it easy."],
        ]
        for block in week:
            lines.extend(block)
        lines.append("\n## Progression rules (how it adapts)")
        lines.append("- If you feel better and want to restart: we’ll add **1 short strength session** next week.")
        lines.append("\n## Safety notes")
        lines.append("- If you have a medical condition or severe pain, get professional advice before increasing intensity.")
        contains_cardio = False
        return PlanOutput(
            headline=headline,
            details=_join_lines(lines),
            meta={
                "contains_cardio": contains_cardio,
                "exercise_mode": exercise_mode,
                "low_impact": low_impact,
                "time_tight": time_tight,
                "has_gym": has_gym,
                "has_band": has_band,
            },
        )
    if goal in ["fat_loss", "weight_loss", "lose_weight"]:
        emphasis = "more daily walking + 3 strength days"
    elif goal in ["muscle_gain", "hypertrophy", "strength"]:
        emphasis = "4 strength days + light cardio"
    else:
        emphasis = "balanced: 3 strength + 2 cardio + daily steps"
    if "cardio" in avoid_activities:
        emphasis = "strength + mobility + steps (no cardio per your preference)"
    lines.append(f"- **This week’s emphasis**: {emphasis}.")

    def strength_day(label: str) -> list[str]:
        if has_gym:
            return [
                f"**{label} — Strength (45–60 min)**",
                "- Warm‑up: 5–8 min easy cardio + dynamic legs/shoulders",
                "- Main lifts (3 sets each): leg press or goblet squat (8–12), chest press (8–12), lat pulldown/row (8–12)",
                "- Accessories (2 sets): RDL (10–12), shoulder press (8–12), plank (30–45s)",
                "- Cool‑down: 5 min walk + hamstring/hip flexor stretch",
            ]
        if has_band:
            return [
                f"**{label} — Strength (30–45 min)**",
                "- Warm‑up: 5 min brisk walk + mobility",
                "- Circuit (3 rounds): band squat (10–15), band row (10–15), band chest press (8–12), band RDL (10–15), side plank (20–30s/side)",
                "- Finish: calf raises (2x12–20) + stretch",
            ]
        return [
            f"**{label} — Strength (25–40 min)**",
            "- Warm‑up: 5 min walk + mobility",
            "- Circuit (3 rounds): chair squat (8–12), incline push‑ups (6–12), hip hinge with backpack (10–12), towel row (8–12), dead bug (6/side)",
            "- Finish: easy walk 5 min + stretch",
        ]

    def cardio_day(label: str) -> list[str]:
        mode = "cycling/elliptical" if low_impact else "brisk walking"
        minutes = 20 if time_tight else 30
        return [
            f"**{label} — Cardio ({minutes} min)**",
            f"- {mode} at **easy-to-moderate** pace (you can speak in short sentences).",
            "- Add **5 min mobility** after.",
        ]

    week = [
        strength_day("Day 1"),
        (["**Day 2 — Mobility + steps (no cardio)**", "- 15–25 min mobility + an easy walk for steps."] if "cardio" in avoid_activities else cardio_day("Day 2")),
        strength_day("Day 3"),
        ["**Day 4 — Recovery**", "- 20–40 min easy walking + gentle stretching."],
        strength_day("Day 5"),
        (["**Day 6 — Mobility + steps (no cardio)**", "- 15–25 min mobility + an easy walk for steps."] if "cardio" in avoid_activities else cardio_day("Day 6")),
        ["**Day 7 — Optional**", "- Fun activity (walk, sport, hike). Keep it easy if you feel fatigued."],
    ]
    for block in week:
        lines.extend(block)

    lines.append("\n## Progression rules (how it adapts)")
    lines.append("- If you complete the week comfortably: add **+5 minutes** to cardio days or **+1 set** to strength circuits next week.")
    lines.append("- If you feel pain, sharp discomfort, or exhaustion: scale down to **2 rounds** and keep cardio easy.")
    lines.append("- If steps are low today: add **2 x 8‑minute walks** (after meals is best).")

    lines.append("\n## Safety notes")
    lines.append("- If you have a medical condition or severe pain, get professional advice before increasing intensity.")

    contains_cardio = "cardio" not in avoid_activities
    return PlanOutput(
        headline=headline,
        details=_join_lines(lines),
        meta={
            "contains_cardio": contains_cardio,
            "exercise_mode": exercise_mode,
            "low_impact": low_impact,
            "time_tight": time_tight,
            "has_gym": has_gym,
            "has_band": has_band,
        },
    )


def generate_diet_plan(*, priorities: list[str], profile: dict, coaching: dict, today: dict, preferences: dict | None = None) -> PlanOutput:
    dietary = (profile.get("dietary_preference") or "").lower()
    allergies = (profile.get("allergies") or "").strip()
    goal = (profile.get("goal") or "general_fitness").lower()
    preferences = preferences or {}
    learned_dietary = (preferences.get("dietary_pattern") or "").strip().lower()
    if learned_dietary:
        dietary = learned_dietary
    avoid_foods_raw = preferences.get("avoid_foods") or "[]"
    try:
        import json as _json
        avoid_foods = set(_json.loads(avoid_foods_raw))
    except Exception:
        avoid_foods = set()

    water_goal = int(coaching["water_goal"])
    headline = "Your personalized nutrition plan (practical + detailed)"

    lines: list[str] = []
    lines.append("## Targets (simple, consistent)")
    lines.append("- **Plate method** most meals: ½ veggies, ¼ protein, ¼ carbs + healthy fats.")
    lines.append("- **Protein anchor** each meal to support recovery and appetite control.")
    lines.append(f"- **Hydration**: aim for **{water_goal} glasses/day** (spread out).")
    if allergies:
        lines.append(f"- **Allergies/intolerances noted**: {allergies}")

    lines.append("\n## What to eat (templates)")
    pref_hint = ""
    if "veg" in dietary:
        pref_hint = " (vegetarian-friendly)"
    elif "vegan" in dietary:
        pref_hint = " (vegan-friendly)"
    lines.append(f"- **Breakfast template{pref_hint}**:")
    if any(x in avoid_foods for x in ["dairy", "milk"]):
        lines.append("  - Option A: eggs/tofu scramble + fruit + nuts (or soy yogurt if you want a yogurt option)")
    else:
        lines.append("  - Option A: eggs/Greek yogurt + fruit + nuts (swap tofu/soy yogurt if needed)")
    lines.append("  - Option B: oatmeal + protein (milk/soy) + berries + seeds")
    lines.append("- **Lunch/Dinner template**:")
    lines.append("  - Protein: chicken/fish/beans/tofu")
    lines.append("  - Carbs: rice/potato/whole grains")
    lines.append("  - Veggies: 2+ cups")
    lines.append("  - Fats: olive oil/avocado/nuts (small portion)")

    lines.append("\n## 1‑day sample menu (customizable)")
    if any(x in avoid_foods for x in ["dairy", "milk"]):
        lines.append("- **Breakfast**: oatmeal + berries + seeds + soy yogurt/tofu")
    else:
        lines.append("- **Breakfast**: oatmeal + berries + seeds + yogurt/tofu")
    lines.append("- **Snack**: fruit + nuts (or hummus + carrots)")
    lines.append("- **Lunch**: big salad bowl + protein + whole-grain wrap/rice")
    if any(x in avoid_foods for x in ["dairy", "milk"]):
        lines.append("- **Snack**: protein shake (non-dairy) / soy yogurt")
    else:
        lines.append("- **Snack**: protein shake / yogurt / soy yogurt")
    lines.append("- **Dinner**: stir-fry veggies + protein + rice; add side salad")

    lines.append("\n## Habit rules (coach mode)")
    if "Water" in priorities:
        lines.append("- **Water rule**: drink **1 glass** after waking, **1** mid‑morning, **1** mid‑afternoon, **1** with dinner (then fill in the rest).")
    else:
        lines.append("- Keep hydration steady: 1 glass with each meal + between meals.")
    if "Sleep" in priorities:
        lines.append("- **Sleep‑support rule**: stop caffeine **8 hours** before bed; keep dinner lighter if reflux affects sleep.")

    lines.append("\n## Grocery list (fast)")
    if any(x in avoid_foods for x in ["dairy", "milk"]):
        lines.append("- Proteins: eggs/tofu/beans/chicken/fish (skip dairy; use soy yogurt if desired)")
    else:
        lines.append("- Proteins: eggs/Greek yogurt/chicken/fish/beans/tofu")
    lines.append("- Carbs: oats/rice/potatoes/whole-grain bread")
    lines.append("- Veg: mixed greens, frozen veggies, tomatoes, cucumbers")
    lines.append("- Fats: olive oil, nuts, seeds")

    if goal in ["fat_loss", "weight_loss", "lose_weight"]:
        lines.append("\n## If your goal is fat loss")
        lines.append("- Use **slightly smaller carb portions** at dinner; keep protein + veggies high.")
    elif goal in ["muscle_gain", "hypertrophy", "strength"]:
        lines.append("\n## If your goal is muscle gain")
        lines.append("- Add **one extra protein+carb snack** on training days (e.g., yogurt + banana).")

    return PlanOutput(
        headline=headline,
        details=_join_lines(lines),
        meta={
            "dietary_pattern_used": (dietary or "").strip().lower(),
            "allergies_noted": bool(allergies),
        },
    )
