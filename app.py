import json
import os

import streamlit as st

from research import PRIORITIES, compute_match, run_research

st.set_page_config(page_title="Revision Rhinoplasty Research (Turkey)", page_icon="🔎", layout="wide")

BADGE = {"sourced": "✅ Sourced", "unverified": "⚠️ Unverified", "missing": "❓ Not found"}
CITIES = ["Istanbul", "Ankara", "Izmir", "Antalya", "Bursa", "Adana", "Gaziantep", "Konya"]

st.session_state.setdefault("results", [])
st.session_state.setdefault("saved", {})
st.session_state.setdefault("criteria", None)


def link(label, url):
    return f"[{label}]({url})" if url else label


def fact(label, f):
    """Render one sourced fact with its status badge."""
    if f.get("value"):
        src = f" · {link('source', f.get('source_url'))}" if f.get("source_url") else ""
        note = f"  \n<small>{f['note']}</small>" if f.get("note") else ""
        st.markdown(f"**{label}:** {f['value']}  \n{BADGE[f['status']]}{src}{note}", unsafe_allow_html=True)
    else:
        st.markdown(f"**{label}:** {BADGE['missing']}")


st.title("🔎 Revision Rhinoplasty Research Assistant: Turkey")
st.warning(
    "Research aid only, **not medical advice and not a ranking of surgical quality**. Information comes from public "
    "web pages and may be outdated, incomplete or self-promotional. Verify credentials with the Turkish Ministry of "
    "Health / the relevant professional society, ask for revision-specific case photos, and have a consultation "
    "before paying any deposit."
)

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
    go = st.button("Search", type="primary", use_container_width=True)

    st.divider()
    st.subheader("Saved list file")
    st.download_button("Download saved (JSON)", json.dumps(list(st.session_state.saved.values()), indent=2),
                       "saved_surgeons.json", disabled=not st.session_state.saved, use_container_width=True)
    up = st.file_uploader("Load saved list", type="json")
    if up:
        try:
            for s in json.load(up):
                st.session_state.saved[s["id"]] = s
        except Exception:
            st.error("Could not read that file.")

if go:
    if not api_key:
        st.error("Enter an Anthropic API key.")
    else:
        crit = {"budget": budget or None, "currency": currency, "cities": cities, "priorities": priorities, "notes": notes}
        with st.spinner("Searching public sources and checking citations. This can take a few minutes..."):
            try:
                out = run_research(crit, n=n, api_key=api_key)
                st.session_state.results = out["surgeons"]
                st.session_state.criteria = crit
                st.success(f"Found {len(out['surgeons'])} candidates from {out['pages_retrieved']} retrieved pages.")
            except Exception as e:
                st.error(f"Search failed: {e}")

tab_res, tab_saved, tab_cmp = st.tabs(["Results", f"Saved ({len(st.session_state.saved)})", "Compare"])


def card(s, crit, key):
    with st.container(border=True):
        top, btn = st.columns([5, 1])
        top.subheader(s["name"] + (f" · {s['clinic']}" if s.get("clinic") else ""))
        if s["id"] in st.session_state.saved:
            if btn.button("Remove", key=f"rm_{key}_{s['id']}"):
                del st.session_state.saved[s["id"]]
                st.rerun()
        elif btn.button("💾 Save", key=f"sv_{key}_{s['id']}"):
            st.session_state.saved[s["id"]] = {**s, "criteria": crit}
            st.rerun()

        a, b = st.columns(2)
        with a:
            fact("Location", s["city"])
            fact("Website", s["website"])
            fact("Credentials", s["credentials"])
            fact("Revision experience", s["revision_experience"])
        with b:
            fact("Pricing", s["pricing"])
            if s["pricing"].get("includes"):
                st.caption(f"Includes: {s['pricing']['includes']}")
            st.markdown("**Stated specialties**")
            if s["specialties"]:
                for sp in s["specialties"]:
                    st.markdown(f"- {sp['value']} ({BADGE[sp['status']]}, {link('source', sp.get('source_url'))})")
            else:
                st.markdown(BADGE["missing"])

        st.markdown("**Reviews**")
        if s["reviews"]:
            for r in s["reviews"]:
                kind = {"clinic_site": "🏷️ Self-published (clinic site, treat as marketing)", "third_party": "Independent",
                        "forum": "Forum/anonymous", "news": "News"}.get(r.get("source_type"), "Unknown source type")
                st.markdown(f"- **{r.get('platform','?')}** {r.get('rating') or ''} "
                            f"{('(' + r['review_count'] + ')') if r.get('review_count') else ''}: {r.get('summary','')} "
                            f"· {kind} · {BADGE[r['status']]} · {link('source', r.get('source_url'))}")
        else:
            st.markdown(BADGE["missing"])

        st.markdown("**How this matches your preferences**")
        for icon, label, text, url in compute_match(s, crit):
            st.markdown(f"{icon} **{label}:** {text} {('· ' + link('source', url)) if url else ''}")
        if s["concerns"]:
            st.markdown("**Caveats found**")
            for c in s["concerns"]:
                st.markdown(f"- 🚩 {c}")


with tab_res:
    if not st.session_state.results:
        st.info("Set your preferences in the sidebar and click Search.")
    for s in st.session_state.results:
        card(s, st.session_state.criteria, "res")

with tab_saved:
    if not st.session_state.saved:
        st.info("Nothing saved yet.")
    for s in list(st.session_state.saved.values()):
        card(s, s.get("criteria") or st.session_state.criteria or {"cities": [], "budget": None, "currency": "EUR", "priorities": []}, "sv")


def cell(f):
    if not f.get("value"):
        return "❓ Not found"
    t = str(f["value"]).replace("|", "/").replace("\n", " ")
    return f"{t}<br>{BADGE[f['status']]}" + (f" [src]({f['source_url']})" if f.get("source_url") else "")


with tab_cmp:
    saved = list(st.session_state.saved.values())
    pick = st.multiselect("Choose saved surgeons to compare", [s["id"] for s in saved], default=[s["id"] for s in saved][:4],
                          format_func=lambda i: st.session_state.saved[i]["name"])
    chosen = [st.session_state.saved[i] for i in pick]
    if len(chosen) < 2:
        st.info("Save at least two surgeons and select them to compare.")
    else:
        crit = chosen[0].get("criteria") or st.session_state.criteria
        rows = {
            "City": [cell(s["city"]) for s in chosen],
            "Website": [cell(s["website"]) for s in chosen],
            "Credentials": [cell(s["credentials"]) for s in chosen],
            "Revision experience": [cell(s["revision_experience"]) for s in chosen],
            "Pricing": [cell(s["pricing"]) for s in chosen],
            "Specialties": ["<br>".join(f"{x['value']} ({'✅' if x['status']=='sourced' else '⚠️'})" for x in s["specialties"]) or "❓ Not found" for s in chosen],
            "Reviews": ["<br>".join(f"{r.get('platform','?')} {r.get('rating') or ''} "
                                    f"{'🏷️self-published' if r.get('source_type')=='clinic_site' else ''}" for r in s["reviews"]) or "❓ Not found" for s in chosen],
        }
        if crit:
            for i, s in enumerate(chosen):
                for icon, label, text, _ in compute_match(s, crit):
                    rows.setdefault(f"Match: {label}", [""] * len(chosen))[i] = f"{icon} {text}".replace("|", "/")
        rows["Caveats"] = ["<br>".join("🚩 " + c for c in s["concerns"]) or "none found" for s in chosen]
        md = "| | " + " | ".join(s["name"] for s in chosen) + " |\n|---|" + "---|" * len(chosen) + "\n"
        for k, v in rows.items():
            md += f"| **{k}** | " + " | ".join(x or "❓" for x in v) + " |\n"
        st.markdown(md, unsafe_allow_html=True)
        st.caption("✅ sourced · ⚠️ unverified/self-reported · ❓ not found. Click 'src' links to check the original page.")
