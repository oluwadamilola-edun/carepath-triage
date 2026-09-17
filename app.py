from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from triage import (
    DANGER_SIGNS,
    GENERAL_SYMPTOMS,
    LEVELS,
    handoff_text,
    score_assessment,
    similar_cases,
)

ROOT = Path(__file__).parent

st.set_page_config(
    page_title="CarePath — Primary Healthcare Triage",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

COPY = {
    "en": {
        "kicker": "CAREPATH · NIGERIA",
        "title": "Know when to seek care.",
        "subtitle": "A few questions. An urgency estimate. A clear explanation. Not a diagnosis.",
        "disclaimer": "This prototype does not diagnose malaria, typhoid, or any other disease, and it does not replace a healthcare professional. Febrile illness often needs laboratory testing.",
        "next": "Continue",
        "back": "Back",
        "assess": "See my urgency result",
    },
    "pcm": {
        "kicker": "CAREPATH · NIGERIA",
        "title": "Know when you need hospital or clinic.",
        "subtitle": "Answer small questions. E go show how urgent e be, and why. E no be doctor diagnosis.",
        "disclaimer": "This tool no dey diagnose malaria, typhoid, or any sickness. E no replace nurse or doctor. Fever fit need test.",
        "next": "Continue",
        "back": "Back",
        "assess": "Show my result",
    },
}


def css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"], .stApp { font-family: Manrope, sans-serif; }
        .stApp { background:
            radial-gradient(900px 420px at 8% -8%, rgba(124,58,237,.28), transparent 55%),
            radial-gradient(700px 380px at 100% 0%, rgba(14,165,233,.12), transparent 45%),
            #0B0B10; }
        [data-testid="stHeader"] { background: rgba(11,11,16,.6); }
        .block-container { padding-top: 1.1rem; max-width: 1120px; }
        [data-testid="stSidebar"] { background: #101018; border-right: 1px solid rgba(255,255,255,.06); }
        .hero {
            position: relative; overflow: hidden;
            border: 1px solid rgba(167,139,250,.22);
            background: linear-gradient(180deg, rgba(24,24,35,.95), rgba(12,12,18,.92));
            border-radius: 28px; padding: 28px 30px 22px; margin-bottom: 18px;
        }
        .kicker { letter-spacing: .2em; font-size: .7rem; color: #C4B5FD; font-weight: 800; }
        .hero h1 { margin: 8px 0 0; font-size: 2.35rem; font-weight: 800; color: #F8F7FF; letter-spacing: -.03em; }
        .hero p { color: #B8B8C7; margin: 10px 0 0; font-size: 1.05rem; }
        .disclaimer { margin-top: 14px; color: #DDD6FE; font-size: .86rem; padding: 10px 12px;
            border-radius: 12px; background: rgba(167,139,250,.08); border: 1px solid rgba(167,139,250,.18); }
        .stepper { display:flex; gap:8px; margin: 6px 0 16px; }
        .step { flex:1; padding: 10px 12px; border-radius: 12px; text-align:center; font-size:.8rem; font-weight:700;
            color:#A3A3B2; background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.06); }
        .step.on { color:#F8F7FF; background: rgba(167,139,250,.18); border-color: rgba(167,139,250,.45); }
        .result-wrap { border-radius: 28px; padding: 26px; text-align:center;
            background: radial-gradient(700px 180px at 50% 0%, rgba(255,255,255,.06), transparent 60%), rgba(16,16,24,.9);
            border: 1px solid rgba(255,255,255,.1); margin-bottom: 16px; }
        .result-wrap h2 { margin: 8px 0 6px; font-size: 2rem; font-weight: 800; }
        .muted { color:#A3A3B2; }
        .chip { display:inline-block; padding:5px 11px; border-radius:999px; font-size:.75rem; font-weight:700;
            background: rgba(167,139,250,.16); color:#DDD6FE; margin: 0 4px; }
        .metric-grid { display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; margin: 16px 0 4px; }
        .metric { background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.07); border-radius: 16px; padding: 12px; }
        .metric b { display:block; color:#F4F4F7; font-size:1.05rem; margin-top:4px; }
        .metric span { color:#9CA3AF; font-size:.75rem; letter-spacing:.04em; text-transform:uppercase; }
        .plan-item { padding: 10px 12px; border-radius: 12px; margin-bottom: 8px;
            background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.06); }
        .stButton > button { border-radius: 12px; font-weight: 700; height: 2.8rem; }
        div[data-testid="stCheckbox"] { background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.06);
            border-radius: 12px; padding: 8px 10px; margin-bottom: 6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "page": 0,
        "lang": "en",
        "age": 25,
        "age_months": 6,
        "sex": "Female",
        "pregnant": "No",
        "duration_days": 1,
        "setting": "Urban / peri-urban",
        "season": "Dry season",
        "temperature_c": "I don't know",
        "history": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    for key in list(GENERAL_SYMPTOMS) + list(DANGER_SIGNS) + ["sickle_cell", "hiv", "diabetes", "asthma"]:
        st.session_state.setdefault(key, False)


def reset_symptoms() -> None:
    for key in list(GENERAL_SYMPTOMS) + list(DANGER_SIGNS) + ["sickle_cell", "hiv", "diabetes", "asthma"]:
        st.session_state[key] = False


def apply_demo(name: str) -> None:
    reset_symptoms()
    presets = {
        "mild": {
            "age": 24, "sex": "Female", "pregnant": "No", "duration_days": 1,
            "setting": "Urban / peri-urban", "season": "Dry season",
            "temperature_c": "38.2", "fever": True, "headache": True, "chills": True,
        },
        "clinic": {
            "age": 31, "sex": "Male", "pregnant": "Not applicable", "duration_days": 3,
            "setting": "Rural / hard to reach", "season": "Rainy season",
            "temperature_c": "39.1", "fever": True, "nausea": True, "weakness": True, "diarrhea": True,
        },
        "urgent": {
            "age": 4, "age_months": 6, "sex": "Male", "pregnant": "Not applicable",
            "duration_days": 2, "setting": "Rural / hard to reach", "season": "Rainy season",
            "temperature_c": "39.4", "fever": True, "breathing": True, "confusion": True,
        },
    }
    st.session_state.update(presets[name])
    st.session_state["page"] = 3
    st.session_state["result_key"] = None


def current_answers() -> dict:
    keys = list(GENERAL_SYMPTOMS) + list(DANGER_SIGNS) + [
        "age", "age_months", "sex", "pregnant", "duration_days", "setting", "season",
        "temperature_c", "sickle_cell", "hiv", "diabetes", "asthma",
    ]
    return {k: st.session_state.get(k) for k in keys}


def stepper(page: int) -> None:
    labels = ["You", "Symptoms", "Context", "Result"]
    cells = []
    for i, label in enumerate(labels):
        cls = "step on" if i == page else "step"
        cells.append(f'<div class="{cls}">{i+1} · {label}</div>')
    st.markdown(f'<div class="stepper">{"".join(cells)}</div>', unsafe_allow_html=True)


def gauge(score: int, color: str) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"font": {"color": "#F8F7FF", "size": 36}},
            gauge={
                "axis": {"range": [0, max(30, score)], "tickcolor": "#6B7280"},
                "bar": {"color": color},
                "bgcolor": "rgba(255,255,255,.04)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 8], "color": "rgba(52,211,153,.18)"},
                    {"range": [8, 16], "color": "rgba(251,191,36,.16)"},
                    {"range": [16, 30], "color": "rgba(251,113,133,.16)"},
                ],
            },
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        height=220,
        margin=dict(l=20, r=20, t=20, b=0),
        font={"color": "#F4F4F7"},
    )
    return fig


def contribution_chart(items: list[dict]) -> go.Figure:
    df = pd.DataFrame(items)
    colors = {
        "Danger sign": "#FB7185",
        "Symptom": "#A78BFA",
        "Risk factor": "#38BDF8",
        "Vital sign": "#FBBF24",
    }
    fig = go.Figure(
        go.Bar(
            x=df["points"],
            y=df["feature"],
            orientation="h",
            marker_color=[colors.get(g, "#A78BFA") for g in df["group"]],
            hovertemplate="%{y}: +%{x} · %{customdata}<extra></extra>",
            customdata=df["group"],
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=max(260, 38 * len(df)),
        margin=dict(l=8, r=8, t=8, b=8),
        xaxis=dict(title="Contribution", color="#C9C9D4", gridcolor="rgba(255,255,255,.08)"),
        yaxis=dict(autorange="reversed", color="#F4F4F7"),
        font=dict(color="#F4F4F7"),
    )
    return fig


def nav(page: int, t: dict) -> None:
    left, right = st.columns(2)
    if page > 0 and left.button(t["back"], width="stretch"):
        st.session_state.page = page - 1
        st.rerun()
    label = t["assess"] if page == 2 else t["next"]
    if page < 3 and right.button(label, width="stretch", type="primary"):
        st.session_state.page = page + 1
        st.rerun()


init_state()
css()
t = COPY[st.session_state.lang]

with st.sidebar:
    st.markdown("**CarePath**")
    st.caption("Explainable triage prototype")
    lang = st.radio("Language", ["en", "pcm"], format_func=lambda x: "English" if x == "en" else "Nigerian Pidgin", key="lang")
    st.divider()
    st.markdown("**Live demo**")
    if st.button("Fever + headache + chills", width="stretch"):
        apply_demo("mild")
        st.rerun()
    if st.button("Fever + vomiting + weakness", width="stretch"):
        apply_demo("clinic")
        st.rerun()
    if st.button("Child + breathing + confusion", width="stretch"):
        apply_demo("urgent")
        st.rerun()
    st.divider()
    if st.button("Start over", width="stretch"):
        reset_symptoms()
        st.session_state.page = 0
        st.session_state.result_key = None
        st.rerun()
    if st.session_state.history:
        st.markdown("**This session**")
        for item in reversed(st.session_state.history[-5:]):
            st.caption(f"{item['created_at']} · {item['level'].upper()} · score {item['score']}")

st.markdown(
    f"""
    <div class="hero">
        <div class="kicker">{t["kicker"]}</div>
        <h1>{t["title"]}</h1>
        <p>{t["subtitle"]}</p>
        <div class="disclaimer">{t["disclaimer"]}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

page = st.session_state.page
stepper(page)

if page == 0:
    st.markdown("### Who is this for?")
    a, b, c = st.columns(3)
    a.number_input("Age (years)", min_value=0, max_value=120, key="age")
    if st.session_state.age == 0:
        b.number_input("Age in months (if under 1 year)", min_value=0, max_value=11, key="age_months")
    else:
        b.selectbox("Sex", ["Female", "Male", "Prefer not to say"], key="sex")
        c.selectbox("Pregnant?", ["No", "Yes", "Not applicable"], key="pregnant")
    if st.session_state.age == 0:
        st.selectbox("Sex", ["Female", "Male", "Prefer not to say"], key="sex")
        st.session_state.pregnant = "Not applicable"
    if st.session_state.age < 12:
        st.session_state.pregnant = "Not applicable"
    st.slider("How many days have the symptoms lasted?", 0, 21, key="duration_days")
    st.caption("Children under 5, people who are pregnant, and babies with fever are treated as higher-risk in this prototype.")
    nav(page, t)

elif page == 1:
    st.markdown("### Symptoms")
    st.caption("Select everything that applies. Danger signs override the score and move the result to urgent.")
    left, right = st.columns(2)
    with left:
        st.markdown("**General symptoms**")
        for key, (label, _) in GENERAL_SYMPTOMS.items():
            st.checkbox(label, key=key)
    with right:
        st.markdown("**Danger signs**")
        for key, (label, _) in DANGER_SIGNS.items():
            st.checkbox(label, key=key)
    nav(page, t)

elif page == 2:
    st.markdown("### Extra context that changes care, not a diagnosis")
    c1, c2 = st.columns(2)
    c1.selectbox("Where are you?", ["Urban / peri-urban", "Rural / hard to reach"], key="setting")
    c2.selectbox("Season", ["Dry season", "Rainy season", "Not sure"], key="season")
    st.selectbox(
        "Temperature if you have a thermometer",
        ["I don't know", "36.5", "37.5", "38.2", "39.1", "39.4", "40.0", "40.5"],
        key="temperature_c",
    )
    st.markdown("**Long-term conditions**")
    m1, m2, m3, m4 = st.columns(4)
    m1.checkbox("Sickle cell", key="sickle_cell")
    m2.checkbox("HIV / low immunity", key="hiv")
    m3.checkbox("Diabetes", key="diabetes")
    m4.checkbox("Asthma / lung disease", key="asthma")
    st.caption("These do not name a disease. They change how quickly skilled care is recommended.")
    nav(page, t)

else:
    answers = current_answers()
    result_key = str(sorted(answers.items()))
    if st.session_state.get("result_key") != result_key:
        result = score_assessment(answers)
        st.session_state.result_cache = result
        st.session_state.result_key = result_key
        st.session_state.history.append(
            {"created_at": result["created_at"], "level": result["level"], "score": result["score"]}
        )
    result = st.session_state.result_cache
    meta = LEVELS[result["level"]]

    st.markdown(
        f"""
        <div class="result-wrap">
            <div class="chip">{meta["badge"]}</div>
            <div class="chip">{result["confidence"]}</div>
            <h2 style="color:{meta["color"]}">{meta["label"]}</h2>
            <p style="font-size:1.12rem;margin:6px 0 4px">{meta["action"]}</p>
            <p class="muted">{meta["detail"]}</p>
            <div class="metric-grid">
                <div class="metric"><span>Care window</span><b>{meta["window"]}</b></div>
                <div class="metric"><span>Suggested setting</span><b>{meta["facility"]}</b></div>
                <div class="metric"><span>Completeness</span><b>{int(result["completeness"]*100)}%</b></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    gcol, ccol = st.columns([0.9, 1.2])
    with gcol:
        st.plotly_chart(gauge(result["score"], meta["color"]), width="stretch")
        st.caption("Heuristic score, not a probability of disease.")
    with ccol:
        if result["contributions"]:
            st.plotly_chart(contribution_chart(result["contributions"]), width="stretch")
        else:
            st.info("No symptoms were selected, so the score stays low. That is still not a clean bill of health.")

    tabs = st.tabs(["Care plan", "Why this result", "Clinician handoff", "Similar prototype cases"])
    with tabs[0]:
        if result["clusters"]:
            st.markdown("**Patterns to discuss with a clinician** (not diagnoses)")
            st.write(" · ".join(result["clusters"]))
        for item in result["care_plan"]:
            st.markdown(f'<div class="plan-item">{item}</div>', unsafe_allow_html=True)
        st.markdown("**Return or go urgently if any of these appear**")
        for item in result["watch_for"]:
            st.markdown(f"- {item}")

    with tabs[1]:
        st.write(result["reason"])
        if result["contributions"]:
            for item in result["contributions"]:
                st.markdown(f"- **{item['feature']}** · {item['group']} · +{item['points']}")
        st.markdown("**Rule**")
        st.code(
            "infant fever (<2 months) or any danger sign → URGENT\n"
            "else score ≥ 8 → CLINIC SOON\n"
            "else → MONITOR\n"
            "User input → features → weighted score → class → explanation → next action",
            language="text",
        )

    with tabs[2]:
        text = handoff_text(answers, result)
        st.text_area("Copy or download this for a clinic visit", text, height=260)
        st.download_button("Download handoff note", text, file_name="carepath-handoff.txt", mime="text/plain")
        st.caption("Share this with a clinician. It is a symptom summary, not a lab result or diagnosis.")

    with tabs[3]:
        sim = similar_cases(answers, ROOT / "data" / "prototype_cases.csv")
        if sim.empty:
            st.caption("Prototype case file is missing.")
        else:
            st.write("Nearest rows in the tiny demonstration dataset (Hamming distance on overlapping features). This is not a trained model.")
            st.dataframe(sim, width="stretch", hide_index=True)

    n1, n2 = st.columns(2)
    if n1.button("Edit answers", width="stretch"):
        st.session_state.page = 0
        st.rerun()
    if n2.button("New assessment", width="stretch"):
        reset_symptoms()
        st.session_state.page = 0
        st.session_state.result_key = None
        st.rerun()
