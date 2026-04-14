from __future__ import annotations

import streamlit as st
import pandas as pd

from agent.coach import run_daily_coach, apply_feedback
from agent.learning import get_learning_state
from agent.progress import summarize_progress
from agent.utility import validate_input, INPUT_LIMITS
from database.db import (
    create_user,
    create_tables,
    fetch_recent_health_rows,
    get_coaching_state,
    get_user_profile,
    list_users,
    upsert_user_profile,
)

create_tables()

st.set_page_config(page_title="Health Coach Agent", page_icon="💪", layout="wide")
st.title("Personalized Health Coaching Agent")
st.caption("Utility-based coaching with perception → reasoning → action → learning. (Utility is internal; you see plans + reminders.)")

if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "active_user_id" not in st.session_state:
    st.session_state.active_user_id = 1
if "feedback_status" not in st.session_state:
    st.session_state.feedback_status = None

with st.sidebar:
    st.subheader("User")
    users = list_users()
    user_labels = {u["id"]: u["display_name"] for u in users}
    user_ids = [u["id"] for u in users]
    if st.session_state.active_user_id not in user_labels:
        st.session_state.active_user_id = user_ids[0] if user_ids else 1

    selected = st.selectbox(
        "Active user",
        options=user_ids,
        format_func=lambda uid: f'{user_labels.get(uid, "User")} (id {uid})',
        index=user_ids.index(st.session_state.active_user_id) if user_ids else 0,
    )
    if selected != st.session_state.active_user_id:
        st.session_state.active_user_id = selected
        st.session_state.last_response = None

    new_name = st.text_input("Create new user", value="", placeholder="e.g., Alex")
    if st.button("Add user"):
        if new_name.strip():
            new_id = create_user(new_name.strip())
            st.session_state.active_user_id = new_id
            st.session_state.last_response = None
            st.success(f"Created user: {new_name.strip()}")
        else:
            st.warning("Enter a name first.")

    st.divider()
    st.subheader("Your profile (for personalization)")
    active_user_id = int(st.session_state.active_user_id)
    profile = get_user_profile(user_id=active_user_id)

    name = st.text_input("Name", value=profile.get("name", ""))
    age = st.number_input("Age", min_value=0, max_value=120, value=int(profile.get("age") or 0))
    sex = st.selectbox("Sex", options=["", "female", "male", "other"], index=0 if not profile.get("sex") else ["", "female", "male", "other"].index(profile.get("sex")))
    height_cm = st.number_input("Height (cm)", min_value=0.0, max_value=250.0, value=float(profile.get("height_cm") or 0.0))
    weight_kg = st.number_input("Weight (kg)", min_value=0.0, max_value=400.0, value=float(profile.get("weight_kg") or 0.0))
    goal = st.selectbox("Goal", options=["general_fitness", "fat_loss", "muscle_gain", "strength", "endurance"], index=["general_fitness", "fat_loss", "muscle_gain", "strength", "endurance"].index(profile.get("goal") or "general_fitness"))
    dietary_preference = st.text_input("Diet preference (e.g., veg/vegan/halal)", value=profile.get("dietary_preference", ""))
    allergies = st.text_input("Allergies/intolerances", value=profile.get("allergies", ""))
    injuries = st.text_input("Injuries/limitations", value=profile.get("injuries", ""))
    equipment = st.text_input("Equipment (gym/dumbbells/bands/none)", value=profile.get("equipment", ""))
    schedule = st.text_input("Schedule constraints (e.g., busy, shift work)", value=profile.get("schedule", ""))

    if st.button("Save profile"):
        upsert_user_profile(
            {
                "name": name,
                "age": (None if age == 0 else int(age)),
                "sex": sex,
                "height_cm": (None if height_cm == 0 else float(height_cm)),
                "weight_kg": (None if weight_kg == 0 else float(weight_kg)),
                "goal": goal,
                "dietary_preference": dietary_preference,
                "allergies": allergies,
                "injuries": injuries,
                "equipment": equipment,
                "schedule": schedule,
            },
            user_id=active_user_id,
        )
        st.success("Saved.")

    st.divider()
    st.subheader("Current coaching targets")
    coaching = get_coaching_state(user_id=active_user_id)
    st.metric("Steps/day goal", f'{coaching["steps_goal"]:,}')
    st.metric("Sleep goal", f'{coaching["sleep_goal"]} h')
    st.metric("Water goal", f'{coaching["water_goal"]} glasses')
    st.metric("Exercise goal", f'{coaching["exercise_goal"]} min')
    st.metric("Streak", f'{coaching["streak"]} days')

tab_checkin, tab_plan, tab_progress = st.tabs(["Daily check‑in", "Coach plan", "Progress"])

with tab_checkin:
    st.subheader("Daily check‑in (perception)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        steps = st.number_input("Steps", 0, 100000, value=0)
    with c2:
        sleep = st.number_input("Sleep (hours)", 0.0, 24.0, value=0.0)
    with c3:
        water = st.number_input("Water (glasses)", 0, 50, value=0)
    with c4:
        exercise = st.number_input("Exercise (minutes)", 0, 720, value=0)

    if st.button("Coach me today"):
        raw_today = {"steps": steps, "sleep": sleep, "water": water, "exercise": exercise}
        bounded_today = validate_input(raw_today)
        capped_fields: list[str] = []
        for k in ["steps", "sleep", "water", "exercise"]:
            lo, hi = INPUT_LIMITS[k]
            raw_val = raw_today.get(k)
            safe_val = bounded_today.get(k)
            try:
                if float(raw_val) != float(safe_val):
                    capped_fields.append(f"{k} ({raw_val} -> {safe_val}, allowed {lo}-{hi})")
            except Exception:
                capped_fields.append(f"{k} (invalid input -> {safe_val}, allowed {lo}-{hi})")

        if capped_fields:
            st.warning("Some inputs were outside safe limits and were capped: " + "; ".join(capped_fields))

        resp = run_daily_coach(
            user_id=active_user_id,
            today=raw_today
        )
        st.session_state.last_response = resp
        st.success("Plan generated. Go to the Coach plan tab.")

with tab_plan:
    st.subheader("Coach plan (reasoning → action)")
    resp = st.session_state.last_response
    if not resp:
        st.info("Do a Daily check‑in first.")
    else:
        # Always compute live progress so this tab reflects latest feedback/learning state.
        latest_coaching = get_coaching_state(user_id=active_user_id)
        latest_rows = fetch_recent_health_rows(user_id=active_user_id, limit=21)
        latest_rows = list(reversed(latest_rows)) if latest_rows else []
        live_progress = summarize_progress(latest_rows, coaching=latest_coaching)
        st.info(f"**Weekly progress:** {live_progress.verdict} — {live_progress.message}")
        st.write(f"**Today’s focus:** {', '.join(resp.priorities) if resp.priorities else 'Maintenance'}")
        st.write(f"**Daily trend:** {resp.trend}")
        st.write(f"**Coach message:** {resp.motivation}")
        if getattr(resp, "checkin_advice", None):
            for tip in resp.checkin_advice:
                st.warning(tip)

        st.divider()
        st.subheader("Reminders + motivation")
        for r in resp.reminders:
            st.write(f"- {r}")

        st.divider()
        st.subheader(resp.exercise_headline)
        st.markdown(resp.exercise_plan)

        st.subheader(resp.diet_headline)
        st.markdown(resp.diet_plan)

        st.divider()
        st.subheader("Feedback (learning)")
        if st.session_state.feedback_status:
            kind = st.session_state.feedback_status.get("kind")
            text = st.session_state.feedback_status.get("text", "")
            if kind == "ok":
                st.success(text)
            elif kind == "error":
                st.error(text)
        c1, c2 = st.columns(2)
        with c1:
            adherence = st.selectbox("Did you follow the plan today?", options=["Not yet", "Yes", "No"], index=0)
        with c2:
            rating = st.slider("How helpful was this plan?", min_value=1, max_value=5, value=4)
        feedback_text = st.text_area("What worked / what didn’t? (this updates future plans)", value="")

        if st.button("Submit feedback"):
            adh_val = None
            if adherence == "Yes":
                adh_val = 1
            elif adherence == "No":
                adh_val = 0
            before_learning = get_learning_state(user_id=active_user_id)
            before_targets = get_coaching_state(user_id=active_user_id)
            try:
                updated = apply_feedback(
                    user_id=active_user_id,
                    priorities=resp.priorities,
                    adherence=adh_val,
                    rating=int(rating),
                    text=feedback_text,
                )
                after_learning = get_learning_state(user_id=active_user_id)
                after_targets = get_coaching_state(user_id=active_user_id)
                st.session_state.feedback_status = {"kind": "ok", "text": "Feedback saved. Learning state updated."}

                st.write("**Updated targets:**")
                st.write(updated["coaching"])

                st.write("**Closed-loop evidence (before -> after):**")
                st.json(
                    {
                        "weights": {
                            "before": before_learning.get("weights", {}),
                            "after": after_learning.get("weights", {}),
                        },
                        "threshold": {
                            "before": before_learning.get("threshold"),
                            "after": after_learning.get("threshold"),
                        },
                        "failure_count": {
                            "before": before_learning.get("failure_count"),
                            "after": after_learning.get("failure_count"),
                        },
                        "goals": {
                            "before": before_targets,
                            "after": after_targets,
                        },
                    }
                )
            except Exception as e:
                st.session_state.feedback_status = {"kind": "error", "text": f"Feedback failed to save: {e}"}

with tab_progress:
    st.subheader("Monitoring (progress over time)")
    active_user_id = int(st.session_state.active_user_id)
    rows = fetch_recent_health_rows(user_id=active_user_id, limit=21)
    coaching = get_coaching_state(user_id=active_user_id)
    if not rows:
        st.info("No check-ins yet.")
    else:
        rows = list(reversed(rows))
        chart_data = {
            "steps": [r["steps"] for r in rows],
            "sleep": [r["sleep"] for r in rows],
            "water": [r["water"] for r in rows],
            "exercise": [r["exercise"] for r in rows],
        }
        st.write("**Metric trends (last 21 check-ins)**")
        df = pd.DataFrame(chart_data)
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Steps")
            st.line_chart(df[["steps"]])
            st.caption("Water")
            st.line_chart(df[["water"]])
        with c2:
            st.caption("Sleep")
            st.line_chart(df[["sleep"]])
            st.caption("Exercise")
            st.line_chart(df[["exercise"]])
        summary = summarize_progress(rows, coaching=coaching)
        stats = summary.stats or {}
        ratio = stats.get("attainment_ratio", {})
        metric_status = stats.get("metric_status", {})

        st.divider()
        st.write(f"**Progress verdict:** {summary.verdict} — {summary.message}")
        c1, c2, c3, c4 = st.columns(4)
        metrics = ["steps", "sleep", "water", "exercise"]
        cols = [c1, c2, c3, c4]
        for col, metric in zip(cols, metrics):
            last_avg = (stats.get("last7_avg", {}) or {}).get(metric, 0.0)
            goal = (stats.get("goal", {}) or {}).get(metric, 0.0)
            pct = max(0.0, min(100.0, float(ratio.get(metric, 0.0)) * 100.0))
            with col:
                st.metric(
                    f"{metric.title()} (7d avg)",
                    f"{last_avg:.1f}",
                    delta=f"Goal {goal:.1f}",
                )
                st.progress(pct / 100.0)
                st.caption(f"{pct:.0f}% of goal - {metric_status.get(metric, 'Unknown')}")
        st.dataframe(rows, use_container_width=True)
