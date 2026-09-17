# CarePath

**AI-assisted primary healthcare triage for Nigeria.**

CarePath estimates how urgently someone should seek professional care based on symptoms and risk factors. It does **not** diagnose malaria, typhoid, or any other disease.

## Run locally

```bash
cd CarePath
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## What the prototype does

- 4-step flow: who → symptoms → context → result
- English / Nigerian Pidgin
- Danger-sign override, infant-fever rule, comorbidities, temperature, rural/season context
- Explainable score gauge + feature contributions
- Care plan, return-if list, clinician handoff download
- Similar rows from a tiny demonstration dataset (not a trained model)

## Deploy (Streamlit Community Cloud)

1. Push this folder to a **public GitHub repo** (already set up if you used the CarePath GitHub remote).
2. Open [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **Create app** → pick the repo → branch `main` → main file `app.py`.
4. Wait 1–2 minutes. Submit the `*.streamlit.app` URL.

## Demo scenarios

1. Fever + headache + chills → usually lower / moderate urgency
2. Fever + vomiting + weakness (3 days) → clinical attention soon
3. Fever + difficulty breathing + confusion (child) → urgent

