"""Fictional sample records for testing the UI without spending API credits.

All names, clinics and URLs are invented (.example domains). They exist to exercise layout and
labelling edge cases, not to describe real surgeons.
"""
from research import normalize_surgeon

SAMPLE_DATE = "2026-10-30"
SAMPLE_CRITERIA = {"budget": 3500, "currency": "USD", "cities": ["Istanbul", "Izmir"],
                   "priorities": ["revision_experience", "credentials", "independent_reviews"], "notes": ""}


def S(url, title, stype, date=None):
    return {"source_url": url, "source_title": title, "source_type": stype, "date_stated": date}


# ---------- 1. Long name, several sources, dollar amounts, all price categories ----------
_C1 = "https://yildirim-nasal.example"
_R1 = {
    "sample": True,
    "name": "Prof. Dr. Maximiliano Alexandros Yıldırım-Karaçoban Özgür-Demirtaş, Aesthetic and Reconstructive Nasal Surgery",
    "clinic": "Yıldırım-Karaçoban International Aesthetic & Reconstructive Nasal Surgery Center",
    "city": {"value": "Istanbul", **S(_C1 + "/contact", "Clinic contact page", "clinic_statement")},
    "website": _C1,
    "summary": "Plastic surgeon whose clinic publishes a dedicated revision rhinoplasty page and a revision price list. Independent coverage is limited to one society listing and two review platforms.",
    "revision_evidence": [
        {"claim": "Dedicated 'Revision Rhinoplasty' page describes rib-cartilage reconstruction after prior surgeries.", "scope": "revision_specific",
         **S(_C1 + "/revision-rhinoplasty", "Revision Rhinoplasty (clinic page)", "clinic_statement", "2025-03")},
        {"claim": "General rhinoplasty page lists open and closed approaches.", "scope": "general_rhinoplasty",
         **S(_C1 + "/rhinoplasty", "Rhinoplasty overview (clinic page)", "clinic_statement")},
    ],
    "credentials": [
        {"claim": "Board certified in plastic, reconstructive and aesthetic surgery (stated since 2009).",
         **S(_C1 + "/about", "About the surgeon (clinic page)", "clinic_statement")},
        {"claim": "Listed as a member of an international plastic surgery society.",
         **S("https://society-directory.example/members/yildirim", "Society member directory entry", "professional_society", "2026-01")},
        {"claim": "Operates at a private hospital in Şişli.",
         **S("https://sisli-hospital.example/doctors/yildirim", "Hospital doctor profile", "hospital_page")},
    ],
    "specialties": [{"claim": "Revision rhinoplasty", **S(_C1 + "/about", "About the surgeon (clinic page)", "clinic_statement")},
                    {"claim": "Septoplasty and functional nasal surgery", **S(_C1 + "/about", "About the surgeon (clinic page)", "clinic_statement")}],
    "prices": [
        {"label": "Revision rhinoplasty from $3,200 (~$3,800 with rib graft)", "procedure": "revision", "channel": "clinic",
         "low": 3200, "high": None, "currency": "USD", "starting_from": True,
         "inclusions": ["Surgeon fee", "One night hospital stay"], **S(_C1 + "/prices", "Clinic price list", "clinic_statement", "2025-09")},
        {"label": "Primary rhinoplasty $2,400", "procedure": "primary", "channel": "clinic", "low": 2400, "currency": "USD",
         "starting_from": False, "inclusions": [], **S(_C1 + "/prices", "Clinic price list", "clinic_statement", "2025-09")},
        {"label": "Revision rhinoplasty package EUR 2,950 incl. hotel", "procedure": "revision", "channel": "marketplace",
         "low": 2950, "currency": "EUR", "starting_from": False, "inclusions": ["3 hotel nights", "Airport transfer"],
         **S("https://clinic-marketplace.example/listing/4411", "Marketplace listing #4411", "marketplace_listing", "2026-02")},
        {"label": "Typical Turkey revision rhinoplasty: $2,500–$5,000", "procedure": "revision", "channel": "country_estimate",
         "low": 2500, "high": 5000, "currency": "USD", "starting_from": False, "inclusions": [],
         **S("https://medical-travel-blog.example/turkey-costs", "Turkey cosmetic surgery cost guide", "news_article", "2024-11")},
    ],
    "reviews": [
        {"subject": "surgeon", "scope": "general", "report_type": "rating_summary", "rating": "4.9/5", "review_count": "87",
         "summary": "Aggregate rating for the surgeon across all procedures.", **S("https://reviews-platform.example/dr/yildirim", "Surgeon profile on review platform", "patient_review_platform", "2026-08")},
        {"subject": "clinic", "scope": "general", "report_type": "rating_summary", "rating": "4.2/5", "review_count": "310",
         "summary": "Aggregate rating for the clinic location.", **S("https://maps.example/place/yildirim-clinic", "Clinic listing with ratings", "patient_review_platform", "2026-09")},
        {"subject": "surgeon", "scope": "revision_specific", "report_type": "patient_report",
         "summary": "A reviewer reports paying about $4,000 in total and needing a minor touch-up, and says follow-up messages were answered within a day.",
         **S("https://nose-forum.example/thread/881", "Forum thread: revision experiences", "forum_post", "2025-06")},
    ],
    "priority_evidence": {
        "revision_experience": {"claim": "Dedicated revision page with rib-cartilage reconstruction described.", **S(_C1 + "/revision-rhinoplasty", "Revision Rhinoplasty (clinic page)", "clinic_statement", "2025-03")},
        "credentials": {"claim": "Society directory lists membership.", **S("https://society-directory.example/members/yildirim", "Society member directory entry", "professional_society", "2026-01")},
    },
    "questions": ["Does the revision quote include the rib-cartilage harvest?"],
}

# ---------- 2. Missing prices, marketplace + estimate only, little evidence ----------
_C2 = "https://ankara-nose.example"
_R2 = {
    "sample": True, "name": "Dr. Selin Aydın", "clinic": "Başkent Nasal Aesthetics", "website": _C2,
    "city": {"value": "Ankara", **S(_C2 + "/contact", "Clinic contact page", "clinic_statement")},
    "summary": "Ankara-based surgeon whose site covers general rhinoplasty. No revision-specific content or clinic price was found.",
    "revision_evidence": [{"claim": "Rhinoplasty page mentions 'correction of previous surgery' in one sentence.", "scope": "general_rhinoplasty",
                           **S(_C2 + "/rhinoplasty", "Rhinoplasty page (clinic)", "clinic_statement")}],
    "credentials": [{"claim": "States specialist training in plastic surgery.", **S(_C2 + "/about", "About page (clinic)", "clinic_statement")}],
    "prices": [
        {"label": "Nose job package EUR 2,100 with hotel", "procedure": "unspecified", "channel": "marketplace", "low": 2100,
         "currency": "EUR", "starting_from": False, "inclusions": [], **S("https://clinic-marketplace.example/listing/9021", "Marketplace listing #9021", "marketplace_listing", "2026-05")},
        {"label": "Rhinoplasty in Turkey typically costs $2,000–$4,000", "procedure": "unspecified", "channel": "country_estimate",
         "low": 2000, "high": 4000, "currency": "USD", "starting_from": False, "inclusions": [],
         **S("https://medical-travel-blog.example/turkey-costs", "Turkey cosmetic surgery cost guide", "news_article", "2024-11")},
    ],
    "reviews": [],
}

# ---------- 3. Primary-price trap: only primary / unspecified clinic prices ----------
_C3 = "https://izmir-rhino.example"
_R3 = {
    "sample": True, "name": "Op. Dr. Emre Çelik", "clinic": "Ege Rhinoplasty Studio", "website": _C3,
    "city": {"value": "Izmir", **S(_C3 + "/en/contact", "Contact (clinic)", "clinic_statement")},
    "summary": "Izmir surgeon with a revision section on the clinic site and a published price list for first-time rhinoplasty only.",
    "revision_evidence": [{"claim": "Revision section explains secondary rhinoplasty consultations and shows case photos.", "scope": "revision_specific",
                           **S(_C3 + "/en/revision", "Revision rhinoplasty (clinic)", "clinic_statement", "2024-12")}],
    "credentials": [{"claim": "Listed by a national plastic surgery society as an active member.",
                     **S("https://society-directory.example/members/celik", "Society member directory entry", "professional_society", "2026-03")}],
    "prices": [
        {"label": "Primary rhinoplasty EUR 2,300", "procedure": "primary", "channel": "clinic", "low": 2300, "currency": "EUR",
         "starting_from": False, "inclusions": ["Surgeon fee", "Anesthesia"], **S(_C3 + "/en/prices", "Price list (clinic)", "clinic_statement", "2026-01")},
        {"label": "Rhinoplasty from EUR 1,900", "procedure": "unspecified", "channel": "clinic", "low": 1900, "currency": "EUR",
         "starting_from": True, "inclusions": [], **S(_C3 + "/en/home", "Home page banner (clinic)", "clinic_statement")},
    ],
    "reviews": [{"subject": "surgeon", "scope": "revision_specific", "report_type": "rating_summary", "rating": "5.0/5", "review_count": "6",
                 "summary": "Small number of reviews that mention revision surgery.", **S("https://reviews-platform.example/dr/celik", "Surgeon profile on review platform", "patient_review_platform", "2026-06")}],
}

# ---------- 4. Conflicting price + credential info, and a source that was never retrieved ----------
_C4 = "https://antalya-nasal.example"
_R4 = {
    "sample": True, "name": "Dr. Murat Şahin", "clinic": "Akdeniz Nasal Surgery", "website": _C4,
    "city": {"value": "Antalya", **S(_C4 + "/contact", "Contact (clinic)", "clinic_statement")},
    "summary": "Antalya surgeon who performs primary and revision nasal surgery. Two clinic pages list different revision prices.",
    "revision_evidence": [{"claim": "Revision page lists reconstruction after over-resection.", "scope": "revision_specific",
                           **S(_C4 + "/revision", "Revision rhinoplasty (clinic)", "clinic_statement", "2025-09")}],
    "credentials": [
        {"claim": "Board-certified plastic surgeon since 2009.", **S(_C4 + "/about", "About (clinic)", "clinic_statement")},
        {"claim": "Member of a plastic surgery society since 2012.", **S("https://society-directory.example/members/sahin", "Society member directory entry", "professional_society", "2026-02")},
    ],
    "prices": [
        {"label": "Revision rhinoplasty EUR 3,000", "procedure": "revision", "channel": "clinic", "low": 3000, "currency": "EUR",
         "starting_from": False, "inclusions": [], **S(_C4 + "/prices-2023", "Price list (archived page)", "clinic_statement", "2023-06")},
        {"label": "Revision rhinoplasty EUR 3,800 (rib graft extra)", "procedure": "revision", "channel": "clinic", "low": 3800, "currency": "EUR",
         "starting_from": False, "inclusions": ["Surgeon fee", "Hospital fee"], **S(_C4 + "/prices", "Price list (current page)", "clinic_statement", "2025-09")},
    ],
    "reviews": [{"subject": "surgeon", "scope": "revision_specific", "report_type": "patient_report",
                 "summary": "A reviewer reports needing a second correction after a prior surgeon and says costs were ~$5,000 overall.",
                 **S("https://unretrieved-reviews.example/post/12", "Review post (never retrieved by the search tool)", "forum_post", "2025-10")}],
    "conflicts": [
        {"topic": "revision price", "versions": [
            {"claim": "EUR 3,000", **S(_C4 + "/prices-2023", "Price list (archived page)", "clinic_statement", "2023-06")},
            {"claim": "EUR 3,800 (rib graft extra)", **S(_C4 + "/prices", "Price list (current page)", "clinic_statement", "2025-09")}]},
        {"topic": "certification date", "versions": [
            {"claim": "Board-certified since 2009 (clinic)", **S(_C4 + "/about", "About (clinic)", "clinic_statement")},
            {"claim": "Society member since 2012", **S("https://society-directory.example/members/sahin", "Society member directory entry", "professional_society", "2026-02")}]},
    ],
}

# ---------- 5. Almost empty record + markdown-hostile characters in the name ----------
_R5 = {"sample": True, "name": "Dr. Ayşe_Nur *Test* [Kaya] ~$1_000~", "clinic": None, "summary": "", "city": None, "website": None}

SAMPLE_RAW = [_R1, _R2, _R3, _R4, _R5]

# URLs the (pretend) search tool returned. Note: unretrieved-reviews.example is deliberately absent.
SAMPLE_SEEN = {
    "yildirim-nasal.example", "yildirim-nasal.example/contact", "yildirim-nasal.example/revision-rhinoplasty",
    "yildirim-nasal.example/rhinoplasty", "yildirim-nasal.example/about", "yildirim-nasal.example/prices",
    "society-directory.example/members/yildirim", "sisli-hospital.example/doctors/yildirim",
    "clinic-marketplace.example/listing/4411", "clinic-marketplace.example/listing/9021",
    "medical-travel-blog.example/turkey-costs", "reviews-platform.example/dr/yildirim", "maps.example/place/yildirim-clinic",
    "nose-forum.example/thread/881", "ankara-nose.example", "ankara-nose.example/contact", "ankara-nose.example/rhinoplasty",
    "ankara-nose.example/about", "izmir-rhino.example", "izmir-rhino.example/en/contact", "izmir-rhino.example/en/revision",
    "izmir-rhino.example/en/prices", "izmir-rhino.example/en/home", "society-directory.example/members/celik",
    "reviews-platform.example/dr/celik", "antalya-nasal.example", "antalya-nasal.example/contact",
    "antalya-nasal.example/revision", "antalya-nasal.example/about", "antalya-nasal.example/prices-2023",
    "antalya-nasal.example/prices", "society-directory.example/members/sahin",
}


def load_samples():
    import copy
    return [normalize_surgeon(copy.deepcopy(r), SAMPLE_SEEN, SAMPLE_DATE) for r in SAMPLE_RAW]
