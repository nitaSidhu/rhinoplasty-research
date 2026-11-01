import hashlib
import json
import os
from datetime import date
from urllib.parse import quote

import streamlit as st

import research
from research import (PRICE_GROUP_ORDER, PRICE_GROUP_TITLES, PRIORITIES, SCOPE_LABELS, SOURCE_TYPES, SUBJECT_LABELS,
                      collect_sources, compute_match, esc, fmt_amount, md_url, price_group, quote_as_price,
                      revision_prices, sanitize_loaded, sanitize_quote, verification)
from sample_data import SAMPLE_CRITERIA, load_samples

st.set_page_config(page_title="Revision Rhinoplasty Research (Turkey)", page_icon="🔎", layout="wide")
st.markdown(
    """<style>
    [data-testid="stMarkdownContainer"] {overflow-wrap:anywhere; word-break:break-word;}
    [data-testid="stMain"] .block-container {max-width: 100%; overflow-x: hidden;}
    .stButton button, [data-testid="stLinkButton"] a {white-space: normal; height: auto; min-height: 2.5rem;}
    </style>""", unsafe_allow_html=True)  # static CSS only; no web content is ever rendered as HTML

CITIES = ["Istanbul", "Ankara", "Izmir", "Antalya", "Bursa", "Adana", "Gaziantep", "Konya"]
DEFAULT_CRIT = {"budget": None, "currency": "EUR", "cities": [], "priorities": [], "notes": ""}
MAX_COMPARE = 4

for k, v in {"results": [], "saved": {}, "criteria": None, "quotes": {}, "compare_ids": [],
             "search_cache": {}, "last_import": None}.items():
    st.session_state.setdefault(k, v)


# ---------------------------------------------------------------- state helpers (no network)
def known():
    d = {s["id"]: s for s in st.session_state.results}
    d.update(st.session_state.saved)
    return d


def crit_for(s):
    return s.get("criteria") or st.session_state.criteria or DEFAULT_CRIT


def toggle_save(sid):
    saved = st.session_state.saved
    if sid in saved:
        del saved[sid]
    elif sid in known():
        saved[sid] = {**known()[sid], "criteria": st.session_state.criteria or DEFAULT_CRIT}
        st.toast("Saved to shortlist.")


def toggle_compare(sid):
    ids = list(st.session_state.compare_ids)
    if sid in ids:
        ids.remove(sid)
    elif len(ids) >= MAX_COMPARE:
        st.toast(f"You can compare up to {MAX_COMPARE} surgeons at a time.")
    else:
        ids.append(sid)
        st.toast("Added. Open the Compare tab to see the comparison.")
    st.session_state.compare_ids = ids


def load_sample():
    st.session_state.results = load_samples()
    st.session_state.criteria = dict(SAMPLE_CRITERIA)


def add_quote(sid, k):
    ss = st.session_state
    q = sanitize_quote({
        "amount": ss.get(f"qa_{k}"), "currency": ss.get(f"qc_{k}"), "starting_from": ss.get(f"qs_{k}"),
        "date": ss.get(f"qd_{k}"), "note": ss.get(f"qn_{k}"),
        "inclusions": [x.strip() for x in (ss.get(f"qi_{k}") or "").split(",") if x.strip()],
        "entered_at": date.today().isoformat()})
    if q and q["amount"]:
        ss.quotes.setdefault(sid, []).append(q)
    else:
        st.toast("Enter an amount greater than zero.")


def delete_quote(sid, i):
    qs = st.session_state.quotes.get(sid, [])
    if 0 <= i < len(qs):
        qs.pop(i)


def export_payload():
    return [{**s, "user_quotes": st.session_state.quotes.get(sid, [])} for sid, s in st.session_state.saved.items()]


# ---------------------------------------------------------------- markdown builders (all dynamic text escaped)
def src_md(src):
    return "No source cited" if not src else f"[{esc(src['title'])}]({md_url(src['url'])})"


def meta_md(src, d=None):
    when = f"page date {esc(d)}" if d else "no date stated on page"
    if not src:
        return f"No source cited · Not independently verified · {when}"
    return f"{src_md(src)} · {SOURCE_TYPES[src['type']]} · {verification(src)} · {when}"


def fact_md(f):
    return f"{esc(f['claim'])}  \n{meta_md(f['src'], f.get('date'))}"


def bullet(md):
    return "- " + md.replace("\n", "\n  ")


def price_md(p):
    amount = fmt_amount(p)
    lines = []
    if amount:
        lines.append(f"**{esc(amount)}**")
        if p.get("label") and p["label"].strip() != amount and p["category"] != "user_quote":
            lines.append(f"Shown on source as: “{esc(p['label'])}”")
    else:
        lines.append(f"**No numeric amount.** Source text: “{esc(p.get('label') or 'not given')}”")
    lines.append("Listed inclusions: " + esc("; ".join(p["inclusions"])) if p["inclusions"] else "Inclusions not stated.")
    if p["category"] == "user_quote":
        lines.append(f"Entered by you{' on ' + esc(p['entered_at']) if p.get('entered_at') else ''}"
                     f" · quote date: {esc(p['date']) if p.get('date') else 'not given'}"
                     + (f" · note: {esc(p['note'])}" if p.get("note") else ""))
    else:
        lines.append(meta_md(p["src"], p.get("date")))
    return "  \n".join(lines)


def revision_split(s):
    rev = [e for e in s["revision_evidence"] if e["scope"] == "revision_specific"]
    gen = [e for e in s["revision_evidence"] if e["scope"] != "revision_specific"]
    return rev, gen


def other_offer_count(s, quotes):
    return sum(1 for p in s["prices"] if p["category"] != "clinic_revision") + len(quotes)


# ---------------------------------------------------------------- result card
def card(s, ctx):
    sid, k = s["id"], f"{ctx}_{s['id']}"
    crit = crit_for(s)
    quotes = st.session_state.quotes.get(sid, [])
    in_short, in_cmp = sid in st.session_state.saved, sid in st.session_state.compare_ids
    with st.container(border=True):
        st.markdown(f"### {esc(s['name'])}")
        place = " · ".join(esc(x) for x in (s.get("clinic"), s.get("city")) if x) or "Clinic and city not found"
        st.caption(f"{place} · Researched {esc(s['researched_at'])}" + (" · **SAMPLE DATA (fictional)**" if s.get("sample") else ""))
        st.markdown(esc(s["summary"]) if s["summary"] else "No summary available.")

        a, b = st.columns(2)
        with a:
            st.markdown("**Revision experience**")
            rev, gen = revision_split(s)
            if rev:
                extra = f"  \n+{len(rev) - 1} more in Detailed findings" if len(rev) > 1 else ""
                st.markdown(fact_md(rev[0]) + extra)
            elif gen:
                st.markdown("No revision-specific evidence found. General rhinoplasty content only (see Detailed findings).")
            else:
                st.markdown("❓ No revision evidence found.")
        with b:
            st.markdown("**Credentials**")
            if s["credentials"]:
                st.markdown("\n".join(bullet(fact_md(c)) for c in s["credentials"][:3]))
                if len(s["credentials"]) > 3:
                    st.caption(f"+{len(s['credentials']) - 3} more in Detailed findings")
            else:
                st.markdown("❓ No credentials found.")
        c, d = st.columns(2)
        with c:
            st.markdown("**Pricing**")
            revs = revision_prices(s)
            if revs:
                st.caption("Clinic-published revision price")
                st.markdown("\n\n".join(price_md(p) for p in revs[:2]))
                if len(revs) > 1:
                    st.caption("Clinic pages list more than one price; see Pricing details.")
            else:
                st.markdown("**Revision price not publicly found.**")
            n_other = other_offer_count(s, quotes)
            if n_other:
                st.caption(f"{n_other} other price mention(s) are listed separately under Pricing details.")
        with d:
            st.markdown("**Questions to clarify**")
            qs = s["questions"]
            st.markdown("\n".join(f"- {esc(q)}" for q in qs[:3]) if qs else "None identified.")
            if len(qs) > 3:
                st.caption(f"+{len(qs) - 3} more in Detailed findings")

        x, y, z = st.columns(3)
        x.button("✓ In shortlist (remove)" if in_short else "Save to shortlist", key=f"sv_{k}", on_click=toggle_save,
                 args=(sid,), use_container_width=True)
        y.button("✓ Comparing (remove)" if in_cmp else "Compare", key=f"cp_{k}", on_click=toggle_compare,
                 args=(sid,), use_container_width=True)
        if s.get("website"):
            z.link_button("Visit website", s["website"], use_container_width=True)
        else:
            z.button("No website found", key=f"nw_{k}", disabled=True, use_container_width=True)
        if s.get("website") and not s.get("website_confirmed"):
            st.caption("Website address was not confirmed in this search. Check it before relying on it.")

        with st.expander("Detailed findings"):
            if rev:
                st.markdown("**Revision-specific evidence**\n" + "\n".join(bullet(fact_md(e)) for e in rev))
            if gen:
                st.markdown("**General rhinoplasty content (not revision-specific)**\n" + "\n".join(bullet(fact_md(e)) for e in gen))
            if s["credentials"]:
                st.markdown("**Credentials** (each claim is labeled separately; one confirmed credential does not confirm the others)\n"
                            + "\n".join(bullet(fact_md(c)) for c in s["credentials"]))
            if s["specialties"]:
                st.markdown("**Stated specialties**\n" + "\n".join(bullet(fact_md(c)) for c in s["specialties"]))
            for cf in s["conflicts"]:
                st.markdown(f"**Sources differ: {esc(cf['topic'])}**\n" + "\n".join(bullet(fact_md(v)) for v in cf["versions"]))
            if len(s["questions"]) > 3:
                st.markdown("**All questions to clarify**\n" + "\n".join(f"- {esc(q)}" for q in s["questions"]))
            if s["legacy_notes"]:
                st.markdown("**Notes from an earlier app version (not re-reviewed)**\n" + "\n".join(f"- {esc(n)}" for n in s["legacy_notes"]))
            if not (s["revision_evidence"] or s["credentials"] or s["specialties"] or s["conflicts"]):
                st.markdown("Nothing further found.")

        with st.expander("Pricing details"):
            st.caption("Prices are shown in the currency of the source. Nothing is converted, and inclusions are shown only when the source lists them.")
            groups = {cat: price_group(s, cat) for cat in PRICE_GROUP_ORDER}
            groups["user_quote"] = [quote_as_price(q) for q in quotes]
            for cat in PRICE_GROUP_ORDER:
                st.markdown(f"**{PRICE_GROUP_TITLES[cat]}**")
                if groups[cat]:
                    st.markdown("\n\n".join(price_md(p) for p in groups[cat]))
                elif cat == "clinic_revision":
                    st.markdown("Revision price not publicly found.")
                elif cat in ("marketplace", "country_estimate", "user_quote"):
                    st.markdown("None found." if cat != "user_quote" else "None entered.")

        with st.expander("Reviews"):
            if not s["reviews"]:
                st.markdown("❓ No reviews found in the pages this search could read. Google Maps ratings usually can't be read automatically, so check them yourself.")
            ratings = [r for r in s["reviews"] if r["report_type"] == "rating_summary"]
            reports = [r for r in s["reviews"] if r["report_type"] == "patient_report"]
            for subj in ("surgeon", "clinic", "unspecified"):
                grp = [r for r in ratings if r["subject"] == subj]
                if grp:
                    st.markdown(f"**{SUBJECT_LABELS[subj]}s**" if subj != "unspecified" else f"**{SUBJECT_LABELS[subj]}**")
                    for r in grp:
                        head = " ".join(x for x in (r["rating"], f"({r['count']} reviews)" if r["count"] else "") if x) or "No rating shown"
                        st.markdown(bullet(f"**{esc(head)}** · {SCOPE_LABELS[r['scope']]}  \n{esc(r['summary'])}  \n{meta_md(r['src'], r['date'])}"))
            if reports:
                st.markdown("**Unverified patient reports** (individual claims, not confirmed)")
                for r in reports:
                    st.markdown(bullet(f"{SCOPE_LABELS[r['scope']]} · {SUBJECT_LABELS[r['subject']].replace(' rating', '')}  \n"
                                       f"{esc(r['summary'])}  \n{meta_md(r['src'], r['date'])}"))
            st.caption("Ratings on a clinic's own site are marketing. Surgeon and clinic ratings are never combined.")

        with st.expander("Sources and what each one supports"):
            st.caption("Source type describes who published the page. Verification describes whether an independent body confirms it. "
                       "Both are assigned automatically from the page the research step read; open the page to confirm.")
            for e in collect_sources(s):
                src = e["src"]
                st.markdown(f"**{src_md(src)}**  \n{SOURCE_TYPES[src['type']]} · {verification(src)} · researched {esc(src['accessed'])}  \n"
                            + "Supports:\n" + "\n".join(f"- {esc(t)}" for t in e["supports"]))
            if not collect_sources(s):
                st.markdown("No sources recorded.")

        with st.expander("Fit with your preferences"):
            rows = compute_match(s, crit)
            if not rows:
                st.markdown("No preferences were set for this search.")
            for icon, label, text, src in rows:
                st.markdown(f"{icon} **{esc(label)}:** {esc(text)}" + (f" ({src_md(src)})" if src else ""))
            st.caption("🟢 matches · 🟡 partly or uncertain · 🔴 does not match · 🔎 evidence found (see its verification label) · ⚪ nothing found. "
                       "This is not a quality ranking.")

        with st.expander("Your personal quotes"):
            for i, q in enumerate(quotes):
                st.markdown(price_md(quote_as_price(q)))
                st.button("Delete this quote", key=f"dq_{k}_{i}", on_click=delete_quote, args=(sid, i))
            with st.form(f"qf_{k}", clear_on_submit=True):
                st.number_input("Amount", min_value=0.0, step=100.0, key=f"qa_{k}")
                st.text_input("Currency exactly as quoted (e.g. EUR, USD, TRY)", key=f"qc_{k}", max_chars=10)
                st.checkbox("It is a 'starting from' quote", key=f"qs_{k}")
                st.text_input("Quote date (optional)", key=f"qd_{k}", max_chars=30)
                st.text_input("Inclusions the quote lists (comma-separated; leave blank if none listed)", key=f"qi_{k}")
                st.text_input("Note (optional)", key=f"qn_{k}", max_chars=200)
                st.form_submit_button("Add quote", on_click=add_quote, args=(sid, k))


# ---------------------------------------------------------------- compare view
def cmp_cell(s, row):
    quotes = st.session_state.quotes.get(s["id"], [])
    missing = "❓ Not found"
    if row == "City":
        return esc(s["city"]) if s["city"] else missing
    if row == "Revision evidence":
        rev, gen = revision_split(s)
        if rev:
            return "\n".join(bullet(fact_md(e)) for e in rev[:2]) + (f"\n- +{len(rev) - 2} more" if len(rev) > 2 else "")
        return "❓ No revision-specific evidence found." + (" General rhinoplasty content only." if gen else "")
    if row == "Credentials and sources":
        return "\n".join(bullet(fact_md(c)) for c in s["credentials"]) or missing
    revs = revision_prices(s)
    if row == "Price type":
        return "Clinic-published revision price" if revs else "Revision price not publicly found."
    if row == "Amount and currency":
        return "\n".join(f"- **{esc(fmt_amount(p) or 'No numeric amount')}**" for p in revs) or "—"
    if row == "Listed inclusions":
        if not revs:
            return "—"
        return "\n".join(f"- {esc('; '.join(p['inclusions'])) if p['inclusions'] else 'Not stated'}" for p in revs)
    if row == "Price source and date":
        return "\n".join(bullet(meta_md(p["src"], p.get("date"))) for p in revs) or "—"
    if row == "Other price mentions (separately labeled)":
        items = []
        for cat in ("marketplace", "country_estimate", "clinic_primary", "clinic_unspecified", "other"):
            for p in price_group(s, cat):
                items.append(f"- {PRICE_GROUP_TITLES[cat].split(' (')[0]}: **{esc(fmt_amount(p) or p['label'])}**")
        for q in quotes:
            items.append(f"- Your quote: **{esc(fmt_amount(quote_as_price(q)))}**")
        return "\n".join(items) or "None"
    if row == "Unanswered questions":
        return "\n".join(f"- {esc(q)}" for q in s["questions"]) or "None identified"
    if row == "Researched":
        return esc(s["researched_at"])
    return ""


CMP_ROWS = ["City", "Revision evidence", "Credentials and sources", "Price type", "Amount and currency", "Listed inclusions",
            "Price source and date", "Other price mentions (separately labeled)", "Unanswered questions", "Researched"]

# ---------------------------------------------------------------- page
st.title("🔎 Revision Rhinoplasty Research Assistant: Turkey")
st.info("Research aid only. This is not medical advice and not a ranking of surgical quality. Public information can be outdated "
        "or self-promotional; confirm details with the clinic and check credentials with the relevant authority.")

with st.sidebar:
    st.header("Your preferences")
    api_key = st.text_input("Anthropic API key", type="password", value=os.getenv("ANTHROPIC_API_KEY", ""))
    c1, c2 = st.columns([2, 1])
    budget = c1.number_input("Budget (surgeon + facility)", min_value=0, value=0, step=500, help="0 = no budget limit")
    currency = c2.selectbox("Currency", ["EUR", "USD", "GBP", "TRY"])
    cities = st.multiselect("Preferred cities", CITIES, default=["Istanbul"])
    priorities = st.multiselect("Priorities", list(PRIORITIES), default=["revision_experience", "credentials"],
                                format_func=PRIORITIES.get)
    notes = st.text_area("Anything else (e.g. nasal obstruction, prior surgery history)", height=90)
    n = st.slider("Max surgeons to look up", 3, 10, 6)
    st.caption("💳 Only the Search button makes paid API calls. Viewing, saving, expanding and comparing never do.")
    force = st.checkbox("Re-run even if this exact search was already done", value=False)
    go = st.button("Search", type="primary", use_container_width=True)
    st.button("Load sample data (no API cost)", on_click=load_sample, use_container_width=True)

    st.divider()
    st.subheader("Shortlist file")
    st.download_button("Download shortlist (JSON)", json.dumps(export_payload(), indent=2, ensure_ascii=False),
                       "saved_surgeons.json", disabled=not st.session_state.saved, use_container_width=True)
    up = st.file_uploader("Load shortlist", type="json")
    if up is not None:
        raw = up.getvalue()
        sig = hashlib.md5(raw).hexdigest()
        if sig != st.session_state.last_import:  # import once per file, not on every rerun
            try:
                data = json.loads(raw)
                data = data.get("surgeons", []) if isinstance(data, dict) else data
                count = 0
                for item in data:
                    s = sanitize_loaded(item)
                    if s:
                        st.session_state.saved[s["id"]] = s
                        qs = [sanitize_quote(q) for q in (item.get("user_quotes") or [])]
                        if any(qs):
                            st.session_state.quotes[s["id"]] = [q for q in qs if q]
                        count += 1
                st.session_state.last_import = sig
                st.toast(f"Loaded {count} surgeon(s). Records from earlier versions were upgraded; their prices are shown as 'procedure not specified'.")
            except Exception:
                st.error("Could not read that file.")

if go:
    crit = {"budget": budget or None, "currency": currency, "cities": cities, "priorities": priorities, "notes": notes}
    cache_key = json.dumps({**crit, "n": n}, sort_keys=True)
    cache = st.session_state.search_cache
    if cache_key in cache and not force:
        st.session_state.results, st.session_state.criteria = cache[cache_key], crit
        st.success("Showing results from an identical earlier search. No API call was made.")
    elif not api_key:
        st.error("Enter an Anthropic API key.")
    else:
        with st.spinner("Searching public sources and checking citations. This can take a few minutes..."):
            try:
                out = research.run_research(crit, n=n, api_key=api_key)
                cache[cache_key] = out["surgeons"]
                st.session_state.results, st.session_state.criteria = out["surgeons"], crit
                st.success(f"Found {len(out['surgeons'])} candidates from {out['pages_retrieved']} retrieved pages.")
            except Exception as e:
                st.error(f"Search failed: {e}")

# keep compare selection valid before the multiselect below is created
all_known = known()
st.session_state.compare_ids = [i for i in st.session_state.compare_ids if i in all_known][:MAX_COMPARE]

tab_res, tab_saved, tab_cmp = st.tabs(["Results", f"Shortlist ({len(st.session_state.saved)})",
                                       f"Compare ({len(st.session_state.compare_ids)})"])

with tab_res:
    if not st.session_state.results:
        st.info("Set your preferences in the sidebar and click Search, or load the sample data to preview the layout.")
    else:
        if any(s.get("sample") for s in st.session_state.results):
            st.warning("Showing fictional sample data for layout testing. These are not real surgeons.")
        st.caption("Results are listed in the order found. The order is not a ranking.")
    for s in st.session_state.results:
        card(s, "res")

with tab_saved:
    if not st.session_state.saved:
        st.info("Nothing in your shortlist yet.")
    for s in list(st.session_state.saved.values()):
        card(s, "sl")

with tab_cmp:
    st.multiselect("Surgeons to compare (up to 4)", list(all_known), key="compare_ids", max_selections=MAX_COMPARE,
                   format_func=lambda i: all_known[i]["name"][:80])
    sel = [all_known[i] for i in st.session_state.compare_ids]
    if len(sel) < 2:
        st.info("Select at least two surgeons, or press Compare on their cards.")
    else:
        st.caption("Rows show what public sources say. Missing information is marked ❓. This view does not rank surgical quality.")
        for row in CMP_ROWS:
            st.markdown(f"#### {row}")
            cols = st.columns(len(sel))
            for col, s in zip(cols, sel):
                col.markdown(f"**{esc(s['name'][:60])}{'…' if len(s['name']) > 60 else ''}**\n\n{cmp_cell(s, row)}")
        if any(st.session_state.quotes.get(s["id"]) for s in sel):
            st.caption("Your personal quotes appear under 'Other price mentions'.")
