# Revision Rhinoplasty Research Assistant (Turkey): v2

    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...
    streamlit run app.py          # or click "Load sample data" in the sidebar: no API key or cost
    python test_samples.py        # offline tests, no network

Files: `app.py` (UI) · `research.py` (search, normalisation, price/source logic) · `sample_data.py` (fictional records) · `test_samples.py`.

## What changed in v2
- Cards: name, clinic/city, <=2-sentence summary, four sections (Revision experience, Credentials, Pricing, Questions to clarify), actions (Save to shortlist, Compare, Visit website). Details, reviews, sources, preference fit and personal quotes are in expanders.
- Pricing is split into: clinic-published REVISION price; marketplace/agency offers; country-level estimates; your personal quotes. Clinic primary-rhinoplasty prices and clinic prices with no stated procedure are shown separately and never as a revision price. No conversion, no inferred inclusions, "Starting from" labeled, original currency and date shown. Otherwise: "Revision price not publicly found."
- Source TYPE (Clinic statement, Professional society source, Patient review platform, Marketplace listing, ...) is separate from VERIFICATION (Independent source / Not independently verified / Unverified report / Source not retrieved). Each credential is labeled on its own. Every source lists the claims it supports.
- "Caveats found" replaced by neutral "Questions to clarify" generated from gaps and conflicts. Conflicts show each version with source and date. Patient claims are labeled unverified reports; surgeon vs clinic ratings and revision-specific vs general reviews are kept apart.
- Compare view: same rows for every surgeon, vertical layout (no horizontal scrolling), no ranking.
- Cost safety: only the Search button calls the API; identical searches are served from a session cache.
- Security: web-sourced text is escaped and never rendered as HTML (the old compare table used unsafe HTML); imported links must be http(s).

## Limitations
- Source-type and "independent" labels are assigned automatically (domain hints + the model's classification). They are an aid, not a verification; open the linked page to confirm.
- Older (v1) shortlist files still import, but their prices become "procedure not specified" and their old caveats appear only as labeled legacy notes.
- Personal quotes are exported only for shortlisted surgeons.
