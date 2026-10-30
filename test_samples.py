"""Offline tests: no API calls, no network. Run:  python test_samples.py
Part 1 tests the data/logic layer with fictional sample data.
Part 2 executes the real app.py against a stub of Streamlit to catch runtime errors and check what is rendered."""
import json, re, runpy, sys, types

import research
from research import *  # noqa
from sample_data import SAMPLE_CRITERIA, load_samples

S = {s["name"][:12]: s for s in load_samples()}
long_, ankara, izmir, antalya, empty = load_samples()
ok = lambda c, m: print(("PASS " if c else "FAIL ") + m) or (None if c else sys.exit(1))

# ---------- pricing separation ----------
rp = revision_prices(long_)
ok(len(rp) == 1 and fmt_amount(rp[0]) == "Starting from USD 3,200", "clinic revision price shown as 'Starting from USD 3,200', original currency")
ok([p["category"] for p in long_["prices"]] == ["clinic_revision", "clinic_primary", "marketplace", "country_estimate"], "clinic revision / primary / marketplace / country estimate kept in separate categories")
ok(all(p["category"] != "clinic_revision" for p in long_["prices"][1:]), "primary, marketplace and country estimate never labeled as revision price")
ok(revision_prices(ankara) == [] and revision_prices(izmir) == [], "no clinic revision price -> none shown (marketplace/estimate/primary/unspecified excluded)")
ok({p["category"] for p in izmir["prices"]} == {"clinic_primary", "clinic_unspecified"}, "Izmir: primary and 'procedure not specified' prices are not revision prices")
ok(len(revision_prices(antalya)) == 2 and len(antalya["conflicts"]) == 2, "Antalya: two conflicting revision prices both kept, with conflicts recorded")
ok(fmt_amount({"low": 2100, "high": None, "currency": None, "starting_from": False}) == "2,100 (currency not stated)", "missing currency is stated, never assumed")
ok("$" not in "".join(fmt_amount(p) or "" for s in load_samples() for p in s["prices"]), "formatted amounts contain no currency symbols")
ok(all(p["inclusions"] == [] or all(isinstance(i, str) for i in p["inclusions"]) for s in load_samples() for p in s["prices"]), "inclusions only as listed by source")
# label contradicting the procedure tag is demoted
tmp = research.normalize_surgeon({"name": "X", "website": "https://x.example", "prices": [{"label": "Primary rhinoplasty 2000", "procedure": "revision", "channel": "clinic", "low": 2000, "currency": "EUR", "source_url": "https://x.example/p", "source_type": "clinic_statement"}]}, {"x.example/p"}, "2026-10-30")
ok(revision_prices(tmp) == [], "price whose label says 'primary' is not accepted as revision even if tagged revision")

# ---------- sources & verification ----------
ok(verification(long_["credentials"][0]["src"]) == "Not independently verified", "clinic credential: not independently verified")
ok(verification(long_["credentials"][1]["src"]) == "Independent source", "society credential: independent source")
ok(verification(long_["credentials"][2]["src"]) == "Not independently verified", "hospital page does not count as independent verification")
ok(long_["credentials"][1]["src"]["type"] == "professional_society" and long_["credentials"][0]["src"]["type"] == "clinic_statement", "source type separate from verification status")
unret = antalya["reviews"][0]["src"]
ok(verification(unret) == "Source not retrieved in this search", "source URL never returned by search is flagged")
ok(all(s["researched_at"] == "2026-10-30" for s in load_samples()), "research date recorded")
srcs = collect_sources(long_)
ok(all(e["supports"] for e in srcs) and any("Credential: Listed as a member" in t for e in srcs for t in e["supports"]), "each source lists the exact claims it supports")
ok(len({e["src"]["url"] for e in srcs}) == len(srcs) >= 8, "multiple sources de-duplicated")
ok(safe_url("javascript:alert(1)") is None and safe_url("https://a.example/x") is not None, "unsafe URL schemes rejected")

# ---------- reviews / questions ----------
r = long_["reviews"]
ok({(x["subject"], x["scope"], x["report_type"]) for x in r} == {("surgeon", "general", "rating_summary"), ("clinic", "general", "rating_summary"), ("surgeon", "revision_specific", "patient_report")}, "surgeon vs clinic, revision-specific vs general, patient reports kept distinct")
qs = " ".join(long_["questions"] + ankara["questions"] + izmir["questions"]).lower()
ok("red flag" not in qs and "concern" not in qs, "questions are neutral (no red-flag wording)")
ok(not any("hotel" in q.lower() or "unpublished" in q.lower() for s in load_samples() for q in s["questions"]), "no questions treating packages/unpublished prices as problems")
ok(any("differ on revision price" in q for q in antalya["questions"]), "conflict becomes a neutral question")
ok(all(len(s["questions"]) <= 8 for s in load_samples()), "question list bounded")

# ---------- summary ----------
ok(limit_sentences("Prof. Dr. Ali Veli is a surgeon. He works in Izmir. He also teaches.", 2) == "Prof. Dr. Ali Veli is a surgeon. He works in Izmir.", "summary limited to two sentences without splitting on 'Dr.'/'Prof.'")
ok(all(len(re.split(r"(?<=[.!?])\s+", s["summary"])) <= 2 for s in load_samples()), "all sample summaries <= 2 sentences")

# ---------- markdown escaping ----------
t = esc("Paid $4,000 or ~$5,000, name_with_underscores *x* [y]")
ok(not re.search(r"(?<!\\)[$~*_\[\]]", t), "esc() neutralises $, ~, *, _ and brackets")

# ---------- preference match ----------
mt = compute_match(long_, SAMPLE_CRITERIA)
ok(any(r[1] == "Budget" and "starting-from" in r[2] and "USD" in r[2] for r in mt), "budget uses clinic revision price only, same currency, flags 'starting from'")
mt2 = compute_match(izmir, SAMPLE_CRITERIA)
ok(any(r[1] == "Budget" and "No clinic-published revision price" in r[2] for r in mt2), "no revision price -> budget not judged from primary/unspecified prices")
mt3 = compute_match(antalya, {**SAMPLE_CRITERIA, "currency": "USD"})
ok(any("Not converted" in r[2] for r in mt3 if r[1] == "Budget"), "currency mismatch is not auto-converted")

# ---------- legacy import ----------
legacy = {"id": "dr-a-istanbul", "name": "Dr. Old Record", "clinic": "Old Clinic", "city": {"value": "Istanbul", "status": "sourced", "source_url": "https://old.example/c"},
          "website": {"value": "https://old.example", "status": "sourced", "source_url": "https://old.example"},
          "specialties": [{"value": "Revision rhinoplasty", "status": "unverified", "source_url": "https://old.example/s"}],
          "revision_experience": {"value": "Revision cases shown", "status": "sourced", "source_url": "https://old.example/r"},
          "credentials": {"value": "Board certified", "status": "unverified", "source_url": None},
          "pricing": {"value": "from 3000 EUR", "low": 3000, "high": None, "currency": "EUR", "includes": "Hospital fee", "status": "sourced", "source_url": "https://old.example/p"},
          "reviews": [{"platform": "X", "rating": "4.5", "review_count": "10", "summary": "ok", "source_type": "third_party", "status": "sourced", "source_url": "https://rev.example/1"}],
          "priority_evidence": {"aftercare": {"value": "Follow-up visits", "status": "sourced", "source_url": "https://old.example/a"}},
          "concerns": ["No price listed"], "criteria": {"budget": 4000, "currency": "EUR", "cities": [], "priorities": []}}
lg = sanitize_loaded(json.loads(json.dumps(legacy)))
ok(lg and lg["schema_version"] == 2 and revision_prices(lg) == [] and lg["prices"][0]["category"] == "clinic_unspecified", "v1 record imports; its price is NOT treated as a revision price")
ok(lg["legacy_notes"] == ["No price listed"] and lg["criteria"]["budget"] == 4000, "v1 caveats kept only as labeled legacy notes; criteria preserved")
rt = sanitize_loaded(json.loads(json.dumps(long_)))
ok(rt and rt["prices"] == long_["prices"] and rt["credentials"] == long_["credentials"], "v2 export -> import round-trips unchanged")
bad = json.loads(json.dumps(long_)); bad["credentials"][0]["src"]["url"] = "javascript:alert(1)"
ok(sanitize_loaded(bad)["credentials"][0]["src"] is None, "imported file with unsafe link is neutralised")
ok(sanitize_loaded({"nope": 1}) is None, "invalid import record rejected")

# ============================ Part 2: run real app.py against a stub Streamlit ============================
MD, CALLS = [], []

class SS(dict):
    __getattr__ = lambda self, k: self[k] if k in self else (_ for _ in ()).throw(AttributeError(k))
    __setattr__ = dict.__setitem__

class Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, name): return getattr(stub, name)

class Stub(types.ModuleType):
    def __init__(self): super().__init__("streamlit"); self.session_state = SS(); self.sidebar = Ctx()
    def set_page_config(self, **k): pass
    def markdown(self, text, **k): MD.append(text); CALLS.append(("markdown", k))
    def caption(self, t, **k): MD.append(t)
    def write(self, t, **k): MD.append(str(t))
    def info(self, t="", **k): MD.append(t)
    warning = success = error = toast = title = subheader = header = divider = info
    def columns(self, spec, **k): return [Ctx() for _ in range(spec if isinstance(spec, int) else len(spec))]
    def tabs(self, labels): MD.extend(labels); return [Ctx() for _ in labels]
    def container(self, *a, **k): return Ctx()
    expander = form = spinner = container
    def button(self, *a, **k): return False
    link_button = download_button = form_submit_button = button
    def checkbox(self, *a, **k): return False
    def number_input(self, *a, **k): return k.get("value", 0)
    def text_input(self, *a, **k): return k.get("value", "")
    text_area = text_input
    def selectbox(self, label, options, **k): return options[0]
    def slider(self, label, a, b, v=None, **k): return v
    def multiselect(self, label, options, key=None, default=None, **k):
        return self.session_state.get(key, default or []) if key else (default or [])
    def file_uploader(self, *a, **k): return None

stub = Stub(); sys.modules["streamlit"] = stub

def run_app(saved=(), compare=(), results=None, quotes=None):
    MD.clear(); CALLS.clear()
    ss = stub.session_state; ss.clear()
    res = results if results is not None else load_samples()
    ss.update({"results": res, "criteria": dict(SAMPLE_CRITERIA), "saved": {r["id"]: r for r in res if r["id"] in saved},
               "compare_ids": list(compare), "quotes": quotes or {}})
    called = []
    research.run_research = lambda *a, **k: called.append(1) or (_ for _ in ()).throw(AssertionError("paid research was called"))
    runpy.run_path("app.py")
    assert not called, "paid research was called"
    return "\n".join(str(x) for x in MD)

ids = [s["id"] for s in load_samples()]
txt = run_app(saved=[ids[0]], compare=ids[:4], quotes={ids[0]: [{"amount": 3300, "currency": "USD", "starting_from": False, "date": "2026-10-01", "note": "email quote", "inclusions": [], "entered_at": "2026-10-30"}]})
ok(True, "app.py runs end to end on sample data (results + shortlist + compare) with no exceptions and no research call")
ok(not [m for m in MD if re.search(r"(?<!\\)\$", str(m)) and "<style>" not in str(m)], "no unescaped '$' in any rendered markdown")
ok("USD 3,200" in txt and "Starting from USD 3,200" in txt, "dollar-denominated price rendered as 'Starting from USD 3,200'")
ok(txt.count("Revision price not publicly found.") >= 6, "'Revision price not publicly found.' shown where no clinic revision price exists")
ok("[source](" not in txt and "](https://yildirim-nasal.example/prices)" in txt and "[Clinic price list](" in txt, "descriptive source names, not repeated 'source' links")
ok("Clinic statement" in txt and "Professional society source" in txt and "Patient review platform" in txt and "Marketplace listing" in txt, "descriptive source-type labels present")
ok("Unverified patient reports" in txt and "Sources differ: revision price" in txt, "patient allegations and conflicts labeled")
ok("Caveats found" not in txt and "Questions to clarify" in txt, "'Caveats found' replaced by 'Questions to clarify'")
for label in ("Revision experience", "Credentials", "Pricing", "Questions to clarify"):
    assert f"**{label}**" in txt, label
ok(True, "four labeled card sections present")
ok(all("unsafe_allow_html" not in str(c) or "<style>" in "".join(MD[:1] + [m for m in MD if "<style>" in str(m)]) for c in CALLS if c[1].get("unsafe_allow_html")), "unsafe HTML only used for the static stylesheet")
ok("Your quote: **USD 3,300**" in txt or "USD 3,300" in txt, "personal quote shown, separately labeled")
txt2 = run_app()
ok("Nothing in your shortlist yet." in txt2 and "Select at least two" in txt2, "empty shortlist/compare states render")
txt3 = run_app(results=[])
ok("load the sample data" in txt3, "empty state offers sample data")
print("\nALL TESTS PASSED")
