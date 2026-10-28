# Revision Rhinoplasty Research Assistant (Turkey)

    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...
    streamlit run app.py

Env options: `ANTHROPIC_MODEL` (default claude-sonnet-5-5), `WEB_SEARCH_TOOL_VERSION`, `MAX_SEARCHES`.
Web search must be enabled for your API organization.

How trust is handled
- Each fact has a status (sourced / unverified / missing) and a source link.
- After the model answers, code downgrades any "sourced" claim whose URL was not actually retrieved in that run.
- Reviews on a clinic's own site are labelled self-published.
- Match summaries are computed by code from the checked data (budget is only compared when currencies match; no FX guessing).
- Saved list persists via JSON download/upload (Streamlit sessions are not persistent).
