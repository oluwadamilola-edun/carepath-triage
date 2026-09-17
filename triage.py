from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

GENERAL_SYMPTOMS = {
    "fever": ("Fever", 3),
    "headache": ("Headache", 2),
    "chills": ("Chills", 2),
    "weakness": ("Body weakness", 2),
    "aches": ("Body aches", 2),
    "nausea": ("Nausea / vomiting", 2),
    "diarrhea": ("Diarrhea", 2),
    "cough": ("Cough", 1),
    "sore_throat": ("Sore throat", 1),
    "rash": ("Rash", 2),
}

DANGER_SIGNS = {
    "breathing": ("Difficulty breathing", 10),
    "confusion": ("Confusion / unusual drowsiness", 10),
    "seizure": ("Seizure / convulsion", 10),
    "unable_drink": ("Unable to drink or breastfeed", 8),
    "persistent_vomiting": ("Persistent vomiting", 7),
    "severe_weakness": ("Unable to stand or walk", 8),
    "dark_urine": ("Dark / bloody urine", 8),
    "jaundice": ("Yellow eyes / skin", 6),
    "bleeding": ("Heavy bleeding", 10),
    "stiff_neck": ("Stiff neck", 9),
    "chest_pain": ("Severe chest pain", 9),
}

CLUSTERS = {
    "Febrile illness pattern": ["fever", "headache", "chills", "aches", "weakness"],
    "Gut / hydration pattern": ["nausea", "diarrhea", "persistent_vomiting", "unable_drink"],
    "Breathing pattern": ["breathing", "cough", "chest_pain"],
    "Neurologic warning pattern": ["confusion", "seizure", "stiff_neck", "headache"],
}

LEVELS = {
    "red": {
        "label": "Urgent attention",
        "badge": "High urgency",
        "color": "#FB7185",
        "facility": "Hospital emergency / urgent care now",
        "action": "Seek emergency medical care immediately.",
        "detail": "Warning signs in this assessment require urgent clinical review. Do not use this tool for treatment or diagnosis.",
        "window": "Go now",
    },
    "yellow": {
        "label": "Clinic or PHC soon",
        "badge": "Moderate urgency",
        "color": "#FBBF24",
        "facility": "Primary health centre or clinic today / next available",
        "action": "See a healthcare professional as soon as possible.",
        "detail": "No emergency danger sign was selected, but the symptom and risk pattern still warrants professional assessment and possible testing.",
        "window": "Within 24 hours",
    },
    "green": {
        "label": "Monitor and reassess",
        "badge": "Lower urgency",
        "color": "#34D399",
        "facility": "Home monitoring, with a PHC visit if symptoms persist",
        "action": "No emergency warning signs were detected in this prototype.",
        "detail": "Keep watching symptoms. Seek care if they worsen, last longer, or any danger sign appears.",
        "window": "Reassess over 24–48 hours",
    },
}


def _bool(answers: dict, key: str) -> bool:
    return bool(answers.get(key))


def infant_fever_urgent(answers: dict) -> bool:
    age_years = int(answers.get("age") or 0)
    age_months = int(answers.get("age_months") or 0)
    under_two_months = age_years == 0 and age_months < 2
    return under_two_months and _bool(answers, "fever")


def score_assessment(answers: dict) -> dict:
    contributions: list[dict] = []
    danger_hits: list[str] = []
    total = 0

    for key, (label, points) in GENERAL_SYMPTOMS.items():
        if _bool(answers, key):
            total += points
            contributions.append({"feature": label, "points": points, "group": "Symptom"})

    for key, (label, points) in DANGER_SIGNS.items():
        if _bool(answers, key):
            total += points
            danger_hits.append(label)
            contributions.append({"feature": label, "points": points, "group": "Danger sign"})

    age = int(answers.get("age") or 0)
    if age < 5:
        total += 5
        contributions.append({"feature": "Age under 5", "points": 5, "group": "Risk factor"})
    if age >= 65:
        total += 3
        contributions.append({"feature": "Age 65+", "points": 3, "group": "Risk factor"})
    if answers.get("pregnant") == "Yes":
        total += 5
        contributions.append({"feature": "Pregnancy", "points": 5, "group": "Risk factor"})
    if int(answers.get("duration_days") or 0) >= 3:
        total += 2
        contributions.append({"feature": "Symptoms lasting 3+ days", "points": 2, "group": "Risk factor"})

    temp = answers.get("temperature_c")
    if temp not in (None, "", "I don't know"):
        try:
            t = float(temp)
            if t >= 40:
                total += 4
                contributions.append({"feature": "Temperature 40°C or higher", "points": 4, "group": "Vital sign"})
            elif t >= 39:
                total += 2
                contributions.append({"feature": "Temperature 39°C or higher", "points": 2, "group": "Vital sign"})
        except (TypeError, ValueError):
            pass

    for key, label, points in (
        ("sickle_cell", "Sickle cell disease", 4),
        ("hiv", "HIV / immunocompromised", 4),
        ("diabetes", "Diabetes", 2),
        ("asthma", "Asthma / chronic lung disease", 2),
    ):
        if _bool(answers, key):
            total += points
            contributions.append({"feature": label, "points": points, "group": "Risk factor"})

    infant_rule = infant_fever_urgent(answers)
    if infant_rule:
        total += 10
        contributions.append({"feature": "Fever in a baby under 2 months", "points": 10, "group": "Danger sign"})
        danger_hits.append("Fever in a baby under 2 months")

    if danger_hits or infant_rule:
        level = "red"
        reason = (
            "A danger sign or an infant-fever rule was triggered. Signs such as impaired "
            "consciousness, convulsions, breathing difficulty, jaundice, abnormal bleeding, "
            "or fever in a very young infant are treated as reasons for urgent assessment."
        )
    elif total >= 8:
        level = "yellow"
        reason = "No emergency danger sign was selected, but the combined score suggests clinical evaluation soon."
    else:
        level = "green"
        reason = "No emergency danger sign was selected, and the combined score is below the clinic-soon threshold in this prototype heuristic."

    selected_keys = [k for k in list(GENERAL_SYMPTOMS) + list(DANGER_SIGNS) if _bool(answers, k)]
    active_clusters = [
        name for name, keys in CLUSTERS.items() if sum(1 for k in keys if k in selected_keys) >= 2
    ]

    completeness = min(1.0, (len(selected_keys) + (1 if answers.get("temperature_c") not in (None, "", "I don't know") else 0)) / 6)
    if level == "red":
        confidence = "High (danger-sign rule)"
    elif completeness < 0.35:
        confidence = "Low information — result may change with more detail"
    else:
        confidence = "Moderate (transparent heuristic, not a clinical model)"

    watch_for = [
        "Difficulty breathing or chest pain",
        "Confusion, seizure, or unusual sleepiness",
        "Unable to drink, breastfeed, or keep fluids down",
        "Persistent vomiting, heavy bleeding, or yellow eyes",
        "Symptoms getting worse instead of better",
    ]
    if _bool(answers, "fever"):
        watch_for.insert(0, "Fever lasting more than 2–3 days, or returning after it seemed to settle")

    care_plan = build_care_plan(level, answers, active_clusters)
    contributions = sorted(contributions, key=lambda x: x["points"], reverse=True)

    return {
        "score": total,
        "level": level,
        "danger_hits": danger_hits,
        "contributions": contributions,
        "reason": reason,
        "clusters": active_clusters,
        "completeness": completeness,
        "confidence": confidence,
        "watch_for": watch_for,
        "care_plan": care_plan,
        "selected_keys": selected_keys,
        "infant_rule": infant_rule,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def build_care_plan(level: str, answers: dict, clusters: list[str]) -> list[str]:
    meta = LEVELS[level]
    plan = [meta["action"], f"Suggested care setting: {meta['facility']}."]
    if answers.get("setting") == "Rural / hard to reach":
        plan.append("If the nearest clinic is far, do not delay travel when urgency is high. Ask family or community health workers for the fastest route to skilled care.")
    if "Febrile illness pattern" in clusters or _bool(answers, "fever"):
        plan.append("Fever can come from many illnesses. WHO recommends diagnostic testing for suspected malaria rather than treating from symptoms alone.")
    if answers.get("season") == "Rainy season" and _bool(answers, "fever"):
        plan.append("Rainy-season fever still needs testing — seasonality is context, not a diagnosis.")
    if "Gut / hydration pattern" in clusters:
        plan.append("If a clinician has not advised otherwise, frequent sips of oral fluids (or ORS if available) can help while you arrange care. Stop and get urgent help if the person cannot drink.")
    if answers.get("pregnant") == "Yes":
        plan.append("Pregnancy increases the importance of prompt skilled assessment for fever and danger signs.")
    if level == "green":
        plan.append("Rest, drink fluids, and reassess. If you are unsure, a PHC visit is still reasonable.")
    plan.append("Nigeria emergency number: 112. This prototype does not replace emergency services.")
    return plan


def handoff_text(answers: dict, result: dict) -> str:
    meta = LEVELS[result["level"]]
    symptoms = [GENERAL_SYMPTOMS[k][0] for k in GENERAL_SYMPTOMS if _bool(answers, k)]
    dangers = result["danger_hits"]
    lines = [
        "CAREPATH CLINICIAN HANDOFF (prototype — not a diagnosis)",
        f"Time: {result['created_at']}",
        f"Urgency: {meta['label'].upper()} | heuristic score {result['score']}",
        f"Age: {answers.get('age')} years",
        f"Sex: {answers.get('sex')} | Pregnant: {answers.get('pregnant')}",
        f"Duration: {answers.get('duration_days')} day(s) | Setting: {answers.get('setting')}",
        f"Symptoms: {', '.join(symptoms) or 'none selected'}",
        f"Danger signs / rules: {', '.join(dangers) or 'none'}",
        f"Symptom clusters to discuss: {', '.join(result['clusters']) or 'none'}",
        f"Recommendation: {meta['action']}",
        "Note: CarePath does not diagnose malaria, typhoid, or any other disease.",
    ]
    return "\n".join(lines)


CSV_FEATURE_MAP = {
    "fever": "fever",
    "headache": "headache",
    "chills": "chills",
    "vomiting": "nausea",
    "diarrhea": "diarrhea",
    "weakness": "weakness",
    "breathing_difficulty": "breathing",
    "confusion": "confusion",
    "seizure": "seizure",
    "cough": "cough",
}


def similar_cases(answers: dict, csv_path: Path, n: int = 3) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(csv_path)
    feature_cols = [c for c in df.columns if c in CSV_FEATURE_MAP]
    scored = []
    for _, row in df.iterrows():
        dist = sum(int(row[c]) != int(_bool(answers, CSV_FEATURE_MAP[c])) for c in feature_cols)
        scored.append(dist)
    out = df.copy()
    out["hamming_distance"] = scored
    return out.sort_values("hamming_distance").head(n)
