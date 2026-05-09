import json
import os
import re
import numpy as np
import pandas as pd
import networkx as nx

# ── Additional removals (on top of clean_names.json) ───────────────────────────
# Match on email local part (exact) or full email.
ADDITIONAL_REMOVE_LOCALS = {
    "abcnewsnow-editor",    # ABC News newsletter bot
    "admin",                # admin@firstdownsports.com — not a person
    "carrfuturesenergy",    # carrfuturesenergy@carrfut.com — company system account
    "klay",                 # klay@enron.com — duplicate of kenneth.lay@enron.com (#4 vs #2)
    # Duplicate Exchange aliases — keep higher-ranked canonical address
    "vkamins",              # rank 68 — dup of j.kaminski@enron.com (rank 7)
    "vince.kaminski",       # rank ~180 — dup of j.kaminski@enron.com (rank 7)
    "jdasovic",             # rank 136 — dup of jeff.dasovich@enron.com (rank 0)
    "dperlin",              # rank 144 — dup of debra.perlingiere@enron.com (rank 35)
    "scorman",              # rank 145 — dup of shelley.corman@enron.com (rank 63)
    "l..denton",            # rank 114 — dup of rhonda.denton@enron.com (rank 12)
    "steven.kean",          # rank 97 — dup of j..kean@enron.com (rank 39, higher risk)
    "mark.taylor",          # rank 67 — dup of .taylor@enron.com (rank 14, Mark Taylor)
    "allen",                # rank 213 — dup of k..allen@enron.com (rank 167, Phillip Allen)
    # System accounts / malformed data
    "word",                 # not a person
    "10177420",             # numeric ID — system account
    "abraham5",             # malformed local part
    "ameytina",             # system/automated account
    "aforbess",             # system/automated account
    "akimball",             # system/automated account
    "avramnallison",        # malformed — likely concatenated name artifact
    "akoelemay",            # system/automated account
    "bburrell",             # system/automated account
    "choirmats",            # choirmats@aol.com — personal AOL, not Enron employee
    "8888915473",           # phone number used as local part — system/spam
    "8774754543",           # phone number used as local part — system/spam
    "arsystem",             # ARSystem@mailman.enron.com — AR access-request system bot
    "-nikole",              # -nikole@excite.com = Nikki Cole, external personal address
    # Duplicate Exchange alias — Maxine Levingston
    "e..levingston",        # Exchange alias for maxine.levingston@enron.com — keep canonical
    # Additional system / bad entries
    "accountit",            # IT system account
    "akoenig",              # malformed / system account
    "blreese",              # malformed / system account
    "boxerindy",            # non-person external address
    "bounce-app-ippexecs-33275",  # bounce address
    "3dnewsletter",         # newsletter system account
    "ameyer",               # single-word, unresolved
    "01",                   # numeric local part
    "a-letter",             # a-letter@sovereignsociety.com — "Sovereign Society's Offshore A-Letter" newsletter
    "analytics.risk",       # analytics.risk@enron.com — X-From: "Risk Analytics" mailbox, not a person
    "a..bowen",             # Exchange alias for melba.bowen@enron.com (X-From: Bowen, Melba A.)
    "administrator",        # administrator@enron.com — system/admin account, not a person
}

# ── Hardcoded descriptions for top people ──────────────────────────────────────
# Keyed by email local part. Falls back to display_name match for canonical
# addresses with unusual formats (e.g. .taylor@enron.com → "mark.taylor").
DESCRIPTIONS = {
    "jeff.dasovich":    "Dasovich is Enron's most irreplaceable individual by knowledge concentration. As Government Relations Executive, he is the primary conduit between Enron and California energy regulators during the crisis. His 45.8% knowledge risk reflects near-monopoly coverage of regulatory strategy that no other employee replicates at scale.",
    "pete.davis":       "Davis represents the classic infrastructure single-point-of-failure. As the sole operator of the Portland/West Desk scheduling system, his departure would immediately disrupt West Coast energy trading operations. His 43% knowledge risk is entirely driven by operational monopoly, not seniority.",
    "kenneth.lay":      "As Chairman and CEO, Lay's departure creates an authority vacuum across all departments. His knowledge risk of 26% is moderate because executive communications are broadly distributed, but his 95% positional impact reflects the organizational paralysis that follows losing a CEO.",
    "jeff.skilling":    "Skilling bridges executive strategy and quantitative research, a rare combination at Enron. His 25% knowledge risk comes from spanning 4 departments. The 95% positional impact as President and COO means his departure disrupts both strategic direction and operational oversight simultaneously.",
    "tracey.kozadinos": "Kozadinos functions as the information hub for the Office of the Chairman. Despite an Executive Assistant title, she processes and routes critical executive communications. Her 23% knowledge risk reflects deep exposure to cross-departmental strategic discussions that few others access.",
    "veronica.espinoza":"Espinoza holds specialized Structured Finance knowledge that concentrates risk in the derivatives documentation pipeline. Her 17% knowledge risk is elevated because she covers both structured products and general operations, creating dual-domain dependency.",
    "j.kaminski":       "Kaminski leads Enron's Research Group with only 2 other experts sharing his quantitative analysis domain. His 75% positional impact as Managing Director combined with rare expertise makes him an Organizational Emergency. Losing Kaminski would effectively dissolve Enron's internal research capability.",
    "kimberly.nelson":  "Nelson operates across Executive Operations and Legal Transactional domains, an unusual cross-functional position. Her Domain Specialist classification reflects expertise breadth rather than depth, but the combination creates dependencies in two separate departments.",
    "lynette.crawford": "Crawford's IT Operations role carries outsized risk because IT infrastructure knowledge is rarely documented or shared. Her 15% knowledge risk with 8 permanent losses indicates deep system-specific knowledge that cannot be recovered through normal succession.",
    "gerald.nemec":     "Nemec is embedded in Enron's Legal Transactional pipeline, handling day-to-day contract execution. His 14% knowledge risk comes from high-volume deal processing knowledge that is procedural but difficult to transfer quickly to a replacement.",
    "don.baughman":     "Baughman bridges Trading and Corporate Communications, giving him visibility into both deal execution and external messaging. His 13% knowledge risk reflects this cross-functional position rather than deep specialization in either domain.",
    "rhonda.denton":    "Denton specializes in Legal Transactional work with deep Structured Finance overlay. Her 13% knowledge risk and 4 permanent losses indicate specialized contract knowledge in derivatives documentation that few others at Enron possess.",
    "kevin.hyatt":      "Hyatt manages Pipeline Operations with only 2 other experts in the Pipeline and Transportation domain. As VP, his 65% positional impact combined with rare domain expertise makes him an Organizational Emergency. Pipeline operations cannot be learned quickly by a successor.",
    "mark.taylor":      "Taylor handles ECT Legal matters spanning Corporate Governance and Structured Finance. His 12% knowledge risk reflects the legal complexity of Enron's trading entity structure. With 4 permanent losses, his departure creates gaps in compliance knowledge that are slow to rebuild.",
    "tana.jones":       "Jones processes the highest volume of legal transactional work at Enron, making her a throughput bottleneck rather than a knowledge bottleneck. Her 12% risk reflects the operational dependency on her processing capacity in the Structured Finance pipeline.",
    "sara.shackleton":  "Shackleton's expertise in ISDA master agreements and derivatives documentation is shared with few others. Her 11% knowledge risk understates her importance because the Structured Finance pipeline depends on her specialized legal review of every major swap contract.",
    "louise.kitchen":   "As COO of Enron Wholesale Services, Kitchen's knowledge is broadly distributed among her direct reports. Her 11% knowledge risk confirms that her team can cover her expertise areas. The 95% positional impact reflects the coordination and decision-making authority that no subordinate can fully replace.",
    "sally.beck":       "Beck mirrors Kitchen's profile as a Replaceable Executive. Her operational knowledge is well-distributed, but her COO authority over Wholesale Operations means her departure disrupts reporting chains and approval workflows across multiple trading desks.",
    "steven.kean":      "Kean serves as Chief of Staff bridging the executive suite with Regulatory and Government Affairs. His 8% knowledge risk is low because his role is coordination, not specialized expertise. His 85% positional impact reflects the difficulty of replacing a trusted executive gatekeeper.",
    "rick.buy":         "Buy oversees enterprise risk management with an 85% positional impact. His knowledge risk is only 7% because risk frameworks are well-documented and his team is capable. The gap his departure creates is in risk governance authority, not analytical capability.",
}


def _lookup_description(person_email: str, dn: str):
    """Return hardcoded description by local part, with display_name fallback."""
    lp = person_email.split("@")[0]
    if lp in DESCRIPTIONS:
        return DESCRIPTIONS[lp]
    # Fallback: match by display_name → "Firstname Lastname" → "firstname.lastname"
    dn_key = dn.lower().replace(" ", ".")
    return DESCRIPTIONS.get(dn_key)


# ── Runtime system-account detection ───────────────────────────────────────────
_SYSTEM_PATTERNS = re.compile(
    r"(^[0-9]|bounce|newsletter|app-|noreply|no-reply|postmaster|mailer-daemon"
    r"|listserv|autorespond|subscribe|unsubscribe|donotreply|notification|alert"
    r"|daemon|system|support|service|info@|abuse@)",
    re.IGNORECASE,
)

def is_system_account(email: str) -> bool:
    """Heuristic: returns True for emails that look like automated accounts."""
    lp = email.strip().lower().split("@")[0]
    if _SYSTEM_PATTERNS.search(lp):
        return True
    # Purely numeric local parts
    if lp.isdigit():
        return True
    # Very short single-word with digits
    if len(lp) <= 6 and any(c.isdigit() for c in lp):
        return True
    return False

# ── Name overrides (applied after clean_names.json) ────────────────────────────
# Keys are email local parts (lowercase). Values are clean display names.
NAME_OVERRIDES = {
    "abillings":    "Aiysha Billings",   # X-From: Aiysha Billings <abillings@knowledgeinenergy.com>
    "afpaschke":    "Al Paschke",        # X-From: Paschke, Al - TM <afpaschke@bpa.gov>
    "a..lee":       "Patricia Lee",      # X-From: Lee, Patricia A. (Exchange alias a..lee@enron.com)
    "a..knudsen":   "Sheila Knudsen",    # X-From: Knudsen, Sheila A. (Exchange alias)
    "a..cordova":   "Karen Cordova",     # X-From: Cordova, Karen A.
    "a..cummings":  "David Cummings",    # X-From: Cummings, David A.
    "a..rodriguez": "Nadia Rodriguez",   # X-From: Rodriguez, Nadia A.
    "amosher":      "Allen Mosher",      # X-From: Mosher, Allen <AMosher@APPAnet.org>
    "allen":            "Phillip Allen",     # allen@enron.com = Phillip K Allen (duplicate)
    "ahafner2":         "Adam Hafner",       # ahafner2@csc.com — per spec
    "beverict":         "Tim Beverick",      # X-From: Beverick, Tim <BevericT@kochind.com>
    ".elizondo":        "Rudy Elizondo",     # .elizondo@enron.com Exchange alias → Elizondo, Rudy (ETS)
    "maxine.levingston":"Maxine Levingston", # canonical form for e..levingston Exchange alias
    "ablanchard":       "Amy Blanchard",     # X-From: "Amy Blanchard" <ablanchard@idgbooks.com>
    "agrasso":          "Anthony Grasso",     # X-cc: "Grasso, Anthony (CICG - NY Equity Ops)" <AGrasso@exchange.ml.com>
    "a..schroeder":     "Mark Schroeder",    # X-From: Schroeder, Mark A. — Exchange alias for mark.schroeder@enron.com
    "a..bowen":         "Melba Bowen",       # X-From: Bowen, Melba A. — Exchange alias of melba.bowen@enron.com
}

# ── Per-person fallback topic categories (for no/sparse expertise profiles) ────
PERSON_TOPIC_OVERRIDES = {
    # lynette.crawford has only 12 archived emails — no expertise profile generated.
    # Role confirmed from headers: IT/Telephony coordinator in ET&S.
    "lynette.crawford@enron.com": ["IT Operations", "Corporate Communications"],
    # ian@isanderson.com is an external Canadian gas consultant (GISB standards work).
    "ian@isanderson.com": ["Legal & Compliance", "Trading Operations"],
    # pete.davis@enron.com — "Schedule Crawler" bot persona; West Desk scheduling analyst.
    # All top topics are Trading Operations (ISO/CAISO scheduling automation).
    "pete.davis@enron.com": ["Trading Operations", "General Operations"],
}

# ── Real Enron titles — keyed by email local part (lowercase) ──────────────────
# These override graph-metric-inferred roles with historically accurate titles.
REAL_TITLES = {
    "kenneth.lay":      "Chairman & CEO",
    "jeff.skilling":    "President & COO",
    "j..kean":          "EVP & Chief of Staff",        # Exchange alias for Steven Kean
    "rick.buy":         "EVP & Chief Risk Officer",
    "james.derrick":    "EVP & General Counsel",
    "louise.kitchen":   "COO, Enron Wholesale Services",
    "sally.beck":       "COO, Enron Wholesale Operations",
    "jeff.dasovich":    "Government Relations Executive",
    "richard.shapiro":  "VP, Regulatory & Government Affairs",
    "mark.haedicke":    "Managing Director, ENA Legal",
    "kevin.hyatt":      "VP, Pipeline Operations",
    "barry.tycholiz":   "VP, Trading",
    "stanley.horton":   "CEO, Enron Transportation Services",
    "john.lavorato":    "CEO, Enron Americas",
    "kevin.presto":     "VP, Trading",
    "sara.shackleton":  "Legal Specialist, ENA Legal",
    "tana.jones":       "Legal Specialist, ENA Legal",
    "debra.perlingiere":"Legal Specialist, ENA Legal",
    "gerald.nemec":     "Legal Counsel",
    "kay.mann":         "Legal Counsel",
    "elizabeth.sager":  "Legal Counsel",
    ".taylor":          "Legal Counsel, ECT Legal",    # Mark Taylor's canonical alias
    "leslie.hansen":    "Legal Counsel",
    "j.kaminski":       "Managing Director, Research Group",
    "chris.germany":    "Director, East Gas Trading",
    "lance.schuler":    "Managing Director & General Counsel",
    "pete.davis":       "Energy Scheduling Coordinator, Portland/West Desk",
    "don.baughman":     "Director, Trading",
    "tracey.kozadinos": "Executive Assistant, Office of the Chairman",
    "kim.ward":         "Director, Trading Operations",
    "rhonda.denton":    "Legal Specialist",
    "lee.wright":       "VP, Enron Global Markets",
    "lynette.crawford": "IT Operations Coordinator",
    "greg.whalley":     "President, Enron Wholesale",
    "richard.sanders":  "VP, Legal",
    "mike.grigsby":     "Director, Gas Trading",
    "john.arnold":      "VP, Trading",
    "drew.fossum":      "VP & General Counsel, Enron Transportation",
    "mark.palmer":      "VP, Communications",
    "jeffrey.shankman": "VP, Global Risk Markets",
    "michelle.cash":    "VP, Human Resources Legal",
}


def get_title(email: str, inferred_role: str) -> str:
    """Return real Enron title if known, else fall back to inferred role."""
    lp = email.strip().lower().split("@")[0]
    return REAL_TITLES.get(lp, inferred_role)


_QUADRANT_COLORS = {
    "Organizational Emergency": "#E21A22",
    "Silent Threat":            "#FF8C00",
    "Replaceable Executive":    "#0072BC",
    "Low Priority":             "#2D8C3C",
}

def compute_quadrant(risk_score: float, pos_impact: float) -> tuple[str, str]:
    kr = risk_score >= 0.12
    pi = pos_impact >= 0.65
    if kr and pi:
        q = "Organizational Emergency"
    elif kr and not pi:
        q = "Silent Threat"
    elif not kr and pi:
        q = "Replaceable Executive"
    else:
        q = "Low Priority"
    return q, _QUADRANT_COLORS[q]


def positional_impact(title: str) -> float:
    """Score 0–1 based on title seniority.

    Compound titles are checked FIRST so they cannot false-match on a
    substring of a more-senior keyword that happens to appear in the title
    (e.g. "Executive Assistant, Office of the Chairman" must not match
    "chairman" at 0.95 — it matches "executive assistant" at 0.15).
    """
    t = title.lower()
    # Compound titles — must precede any single-keyword check they could trigger
    if "executive assistant" in t:
        return 0.15
    if "assistant director" in t:
        return 0.30
    if "assistant vice president" in t or "assistant vp" in t:
        return 0.40
    if "senior analyst" in t or "senior manager" in t:
        return 0.40
    # Single-keyword checks from most to least senior
    # Match standalone CEO/COO (e.g. "CEO, Enron Americas") without catching
    # "coordinator" (which contains "coo" but not "coo," or "coo ")
    if any(x in t for x in ["chairman", "& ceo", "ceo,", "ceo ", "president",
                              "& coo", "coo,", "coo "]):
        return 0.95
    if any(x in t for x in ["evp", "chief "]):
        return 0.85
    if any(x in t for x in ["svp", "managing director"]):
        return 0.75
    if " vp" in t or t.startswith("vp"):
        return 0.65
    if "director" in t:
        return 0.50
    if any(x in t for x in ["analyst", "manager", "specialist", "counsel"]):
        return 0.30
    if "associate" in t:
        return 0.20
    if any(x in t for x in ["junior associate", "coordinator", "assistant"]):
        return 0.15
    return 0.25


def role_category(title: str) -> str:
    """Map a title to a functional role category for successor gating."""
    t = title.lower()
    # Functional designation takes precedence over seniority
    if any(x in t for x in ["legal", "counsel", "attorney", "litigation"]):
        return "Legal"
    if any(x in t for x in ["trading", "trader", "gas trading", "desk"]):
        return "Trading"
    if any(x in t for x in ["research", "quantitative", "analytics"]):
        return "Research"
    if any(x in t for x in ["regulatory", "government", "affairs"]):
        return "Regulatory"
    if any(x in t for x in ["operations", "coordinator", "scheduling",
                              "pipeline", "transportation"]):
        return "Operations"
    if any(x in t for x in ["communications", " pr", "investor"]):
        return "Communications"
    # Seniority-based for those without a functional designator
    if any(x in t for x in ["ceo", "coo", "evp", "chairman", "president",
                              " vp", "managing director"]):
        return "Executive"
    return "Administration"

# ── Role category → topic category (fallback for successor labels when a topic
#    ID is not in the departed person's expertise profile) ─────────────────────
_ROLE_TO_TOPIC_CAT = {
    "Legal":          "Legal — Transactional",
    "Trading":        "Trading Operations",
    "Research":       "Research & Quantitative Analysis",
    "Regulatory":     "Regulatory & Government Affairs",
    "Operations":     "Pipeline & Transportation",
    "Communications": "Corporate Communications",
    "Executive":      "Executive Operations",
    "Administration": "Document Management & Administration",
}

# Domain → default topic categories for external addresses with no expertise profile
_DOMAIN_CATEGORIES = {
    "lemle.com":     ["Legal — Transactional"],
    "winstead.com":  ["Legal — Transactional"],
    "isda.org":      ["Structured Finance & Derivatives"],
    "appanet.org":   ["California Energy Crisis"],   # APPA = American Public Power Assoc
    "bpa.gov":       ["California Energy Crisis"],   # Bonneville Power Administration
}

# Role → fallback topic category for internal accounts with no expertise profile
_ROLE_CATEGORY_FALLBACK = {
    "Executive Leadership":        ["Corporate Communications"],
    "Senior Management":           ["Corporate Communications"],
    "Director":                    ["Corporate Communications"],
    "Domain Specialist":           ["General Operations"],
    "Scheduling Systems Analyst":  ["Trading Operations"],
    "IT Operations Coordinator":   ["Corporate Communications"],
    "Senior Analyst":              ["Trading Operations"],
    "Analyst":                     ["Trading Operations"],
    "Associate":                   ["General Operations"],
    "Junior Associate":            ["General Operations"],
    # Real-title fallbacks
    "Government Relations Executive":      ["Regulatory & Government Affairs"],
    "VP, Regulatory & Government Affairs": ["Regulatory & Government Affairs"],
    "Energy Scheduling Coordinator, Portland/West Desk": ["Trading Operations"],
    "IT Operations Coordinator":           ["Corporate Communications"],
}

# ── Topic categories (12 + General Operations fallback) ─────────────────────────
# Keyword sets per category — high-priority (weight 3) and supporting (weight 1).
# ORDER MATTERS: categories are scored in order; highest score wins.
_CAT_KEYWORDS = {
    "California Energy Crisis": (
        {"california", "electricity", "caiso", "dwr", "cpuc", "socal", "cali",
         "mws", "ferc", "sce", "pge", "curtailment", "iso", "crisis",
         "deregulation", "blackout", "davis", "utility"},
        {"state", "power", "energy", "market", "rate", "customers", "price",
         "demand", "supply", "cap", "caps", "load"}
    ),
    "Structured Finance & Derivatives": (
        {"isda", "swap", "swaps", "netting", "csa", "counterparty",
         "liquidation", "termination", "escrow", "gtc", "bankruptcy",
         "creditors", "derivative", "structured", "credit"},
        {"master", "agreement", "ena", "debt", "ibj", "nda",
         "confidentiality", "committee", "severance", "facility"}
    ),
    "Research & Quantitative Analysis": (
        {"kaminski", "vince", "vkaminski", "resume", "interview", "candidate",
         "mba", "haas", "berkeley", "fma", "quantitative", "analytics",
         "simulation", "candace", "model"},
        {"research", "edu", "school", "rice", "vincent", "shirley",
         "feedback", "performance", "pep", "risk", "associate"}
    ),
    "Trading Operations": (
        {"nymex", "sitara", "enrononline", "mmbtu", "mmcf", "westdesk",
         "hourahead", "deliveries", "lng", "risktrac",
         "intercontinentalexchange", "futures", "clearing", "comex"},
        {"trading", "gas", "deal", "deals", "volume", "nomination",
         "nominations", "trade", "hedge", "metals", "positions",
         "dth", "pool", "mw", "desk", "price", "market"}
    ),
    "Legal — Corporate Governance": (
        {"litigation", "court", "sec", "derrick", "governance", "board",
         "testimony", "discovery", "motions", "privileged", "confidential",
         "attorney", "judge"},
        {"legal", "counsel", "corporate", "compliance", "regulation",
         "authorized", "restricted", "motion", "settlement", "liability"}
    ),
    "Legal — Transactional": (
        {"draft", "comments", "version", "changes", "redline", "exhibit",
         "clause", "provisions", "executed", "counterpart"},
        {"agreement", "contract", "review", "doc", "legal", "counsel",
         "master", "nda", "confidentiality", "amendment", "schedule"}
    ),
    "Regulatory & Government Affairs": (
        {"ferc", "regulatory", "government", "legislature", "political",
         "lobbyist", "commission", "policy", "shapiro", "dasovich"},
        {"federal", "state", "regulation", "affairs", "agency", "rule",
         "filing", "order", "docket", "congress", "senate", "iso"}
    ),
    "Corporate Communications": (
        {"ect", "ees", "ebs", "enron_development", "employees", "skilling",
         "dynegy", "merger", "press", "investor", "announcement"},
        {"enron", "company", "employee", "corp", "management", "president",
         "chairman", "global", "organization", "memo", "communications"}
    ),
    "Pipeline & Transportation": (
        {"pipeline", "ets", "transport", "transmission", "tariff",
         "capacity", "horton", "fossum", "hyatt", "compressor"},
        {"gas", "natural", "flow", "contract", "service", "interstate",
         "regulatory", "ferc", "storage", "delivery", "nominations"}
    ),
    "Risk Management": (
        {"var", "portfolio", "exposure", "hedge", "position", "credit",
         "rick", "buy", "volatility", "correlation", "scenario"},
        {"risk", "market", "limit", "report", "model", "measurement",
         "loss", "capital", "management", "stress"}
    ),
    "Executive Operations": (
        {"meeting", "conference", "room", "appt", "appointment", "evite",
         "rsvp", "office", "calendar"},
        {"call", "00", "30", "schedule", "reservation", "time", "confirmed",
         "doctor", "dentist", "lunch", "dinner", "flight"}
    ),
    "Document Management & Administration": (
        {"attached", "xls", "wpd", "pdf", "presentation", "spreadsheet",
         "fax", "copy", "print", "forward"},
        {"file", "send", "information", "update", "weekly", "format",
         "please", "see", "changes", "draft", "version", "report"}
    ),
}

def _categorize(words):
    """Return category string for a list of top words."""
    w = {x.lower() for x in (words or [])[:8]}
    best_cat, best_score = "General Operations", 0
    for cat, (high, low) in _CAT_KEYWORDS.items():
        score = len(w & high) * 3 + len(w & low)
        if score > best_score:
            best_score, best_cat = score, cat
    return best_cat

def _build_topic_categories(topic_words_raw):
    """Build {str(topic_id): category} mapping from raw topic words dict."""
    return {tid: _categorize(words) for tid, words in topic_words_raw.items()}

# ── Role inference from graph metrics ──────────────────────────────────────────
def infer_role(betweenness, topics_top_expert, weighted_degree):
    if betweenness > 0.03:        return "Executive Leadership"
    if betweenness > 0.015:       return "Senior Management"
    if betweenness > 0.008:       return "Director"
    if topics_top_expert > 3:     return "Domain Specialist"
    if weighted_degree > 5000:    return "Senior Analyst"
    if weighted_degree > 2000:    return "Analyst"
    if weighted_degree > 500:     return "Associate"
    return "Junior Associate"

# ── Clean name data from clean_data.py ─────────────────────────────────────────
print("Loading clean_names.json...")
if os.path.exists("clean_names.json"):
    with open("clean_names.json") as f:
        _clean = json.load(f)
    DISPLAY_NAMES = _clean.get("display_names", {})
    REMOVE_EMAILS = set(e.lower() for e in _clean.get("removed", []))
    DUPLICATE_MAP = {e.lower(): c for e, c in _clean.get("duplicates", {}).items()}
    print(f"  {len(DISPLAY_NAMES)} name entries, {len(REMOVE_EMAILS)} removals, "
          f"{len(DUPLICATE_MAP)} duplicates")
else:
    print("  clean_names.json not found — run clean_data.py first")
    DISPLAY_NAMES = {}
    REMOVE_EMAILS = set()
    DUPLICATE_MAP = {}

# Apply additional removals
REMOVE_EMAILS |= {e.lower() for e in ADDITIONAL_REMOVE_LOCALS}

# Apply name overrides — keyed by local part
for local, name in NAME_OVERRIDES.items():
    # Find any matching email in DISPLAY_NAMES and update it
    for email in list(DISPLAY_NAMES.keys()):
        lp = email.split("@")[0]
        if lp == local:
            DISPLAY_NAMES[email] = name
    # Also ensure the override is in ADDITIONAL_REMOVE_LOCALS check
print(f"  After overrides: {len(DISPLAY_NAMES)} name entries, "
      f"{len(REMOVE_EMAILS)} removals (incl. {len(ADDITIONAL_REMOVE_LOCALS)} additional)")


def display_name(email: str) -> str:
    """Return clean display name for an email address, or formatted fallback."""
    if not email:
        return ""
    key = email.strip().lower()
    # Check full-email match
    if key in DISPLAY_NAMES:
        return DISPLAY_NAMES[key]
    # Check NAME_OVERRIDES by local part
    lp = key.split("@")[0]
    if lp in NAME_OVERRIDES:
        return NAME_OVERRIDES[lp]
    # Fallback: format from email local part
    clean = lp.replace("..", " ").replace(".", " ").replace("_", " ").strip()
    parts = [p for p in clean.split() if p and not p.startswith("'")]
    return " ".join(p.capitalize() for p in parts) if parts else email


def should_remove(email: str) -> bool:
    key = email.strip().lower()
    if key in REMOVE_EMAILS:
        return True
    lp = key.split("@")[0]
    if lp in ADDITIONAL_REMOVE_LOCALS:
        return True
    if is_system_account(email):
        return True
    return False


print("Loading data sources...")

risk = pd.read_parquet("risk_scores.parquet")
ep   = pd.read_parquet("expertise_profiles.parquet")
vuln = pd.read_parquet("topic_vulnerability.parquet")

with open("simulation_results.json") as f:
    sim_results = json.load(f)

print(f"  risk_scores: {len(risk):,} rows")
print(f"  expertise_profiles: {len(ep):,} rows")
print(f"  topic_vulnerability: {len(vuln):,} rows")
print(f"  simulation_results: {len(sim_results)} simulations")

print("Loading knowledge_graph.graphml...")
G = nx.read_graphml("knowledge_graph.graphml")
for u, v, d in G.edges(data=True):
    d["weight"] = float(d.get("weight", 1))
print(f"  Graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")

# ── Topic words ─────────────────────────────────────────────────────────────────
print("\nLoading topic words...")
topic_words_raw = {}

if os.path.exists("topic_words.json"):
    with open("topic_words.json") as f:
        topic_words_raw = json.load(f)
    print(f"  Loaded topic_words.json ({len(topic_words_raw)} topics)")
elif os.path.exists("bertopic_model"):
    print("  topic_words.json not found — loading saved BERTopic model...")
    try:
        import warnings; warnings.filterwarnings("ignore")
        from bertopic import BERTopic
        topic_model = BERTopic.load("bertopic_model")
        topic_info  = topic_model.get_topic_info()
        for _, row in topic_info[topic_info["Topic"] != -1].iterrows():
            tid = int(row["Topic"])
            topic_words_raw[str(tid)] = [w for w, _ in topic_model.get_topic(tid)[:8]]
        print(f"  Extracted {len(topic_words_raw)} topics from saved model")
        with open("topic_words.json", "w") as f:
            json.dump(topic_words_raw, f)
        print("  Cached to topic_words.json")
    except Exception as e:
        print(f"  BERTopic load failed ({e}) — continuing without topic words")
else:
    print("  No topic_words.json or bertopic_model/ found")

topic_words = {
    tid: ", ".join(words[:5])
    for tid, words in topic_words_raw.items()
    if words
}
print(f"  topic_words ready: {len(topic_words)} entries")

# ── Topic categories ─────────────────────────────────────────────────────────────
print("Building topic categories...")
topic_categories = _build_topic_categories(topic_words_raw)
with open("topic_categories.json", "w") as f:
    json.dump(topic_categories, f, indent=2)
# Tally
from collections import Counter
cat_counts = Counter(topic_categories.values())
for cat, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
    print(f"  {n:3d}  {cat}")

def words_for(topic_id):
    return topic_words.get(str(topic_id), "")

def category_for(topic_id):
    return topic_categories.get(str(topic_id), "General Operations")

# ── Top 200 people (after filtering removed accounts) ──────────────────────────
print("\nBuilding people data (top 200 after removals)...")

sim_by_person = {r["person"]: r for r in sim_results}

top_risk = risk.head(300).copy()
top_risk_filtered = top_risk[
    ~top_risk["person"].apply(should_remove)
].head(200)

n_removed = len(top_risk) - len(top_risk[~top_risk["person"].apply(should_remove)])
print(f"  Filtered out {n_removed} accounts from top 300")

# Report any system accounts caught by heuristic (not in explicit lists)
_detected_system = [
    p for p in top_risk["person"]
    if is_system_account(p)
    and p.strip().lower() not in REMOVE_EMAILS
    and p.strip().lower().split("@")[0] not in ADDITIONAL_REMOVE_LOCALS
]
if _detected_system:
    print(f"  System accounts detected by heuristic ({len(_detected_system)}): {_detected_system}")

# ── Pre-compute title + role_category for every top-200 person ─────────────────
# (used to gate successor matching without a second pass)
person_to_title: dict[str, str] = {}
for _, row in top_risk_filtered.iterrows():
    p = row["person"]
    inferred = infer_role(
        betweenness      = float(row["betweenness"]),
        topics_top_expert= int(row["topics_top_expert"]),
        weighted_degree  = float(row["weighted_degree"]),
    )
    person_to_title[p] = get_title(p, inferred)

person_to_category: dict[str, str] = {
    p: role_category(t) for p, t in person_to_title.items()
}

people_data = []
for _, row in top_risk_filtered.iterrows():
    person = row["person"]
    sim    = sim_by_person.get(person, {})

    # Real title (or inferred fallback)
    role = person_to_title[person]
    dep_category = person_to_category[person]

    # 12-month recovery curve
    timeline       = sim.get("monthly_timeline", [])
    recovery_rates = [t.get("recovery_rate", 0.0) for t in timeline]
    while len(recovery_rates) < 12:
        recovery_rates.append(recovery_rates[-1] if recovery_rates else 0.0)
    recovery_rates = recovery_rates[:12]

    # Routing log grouped by month (20 entries per month max)
    routing_log_raw  = sim.get("routing_log", [])
    routing_by_month = {}
    for entry in routing_log_raw:
        m = str(entry.get("month", 1))
        if m not in routing_by_month:
            routing_by_month[m] = []
        if len(routing_by_month[m]) < 20:
            agent_email = entry.get("agent")
            tid = entry.get("topic")
            routing_by_month[m].append({
                "topic":          tid,
                "topic_words":    words_for(tid),
                "topic_category": category_for(tid),
                "step":           entry.get("step"),
                "quality":        round(float(entry.get("quality_ratio", 0.0)), 4),
                "tier":           entry.get("quality", "none"),
                "agent":          agent_email,
                "agent_name":     display_name(agent_email) if agent_email else "",
            })

    # Topic profile: top 10 topics by score
    person_topics = (
        ep[ep["from"] == person]
        .sort_values("score", ascending=False)
        .head(10)[["topic", "score"]]
        .to_dict("records")
    )
    for t in person_topics:
        t["score"]    = round(float(t["score"]), 4)
        t["words"]    = words_for(t["topic"])
        t["category"] = category_for(t["topic"])

    # Inject fallback topic categories for people with empty expertise profiles
    if not person_topics:
        if person in PERSON_TOPIC_OVERRIDES:
            cats = PERSON_TOPIC_OVERRIDES[person]
        else:
            domain = person.split("@")[-1].lower() if "@" in person else ""
            cats = _DOMAIN_CATEGORIES.get(domain) or _ROLE_CATEGORY_FALLBACK.get(role, ["General Operations"])
        for cat in cats:
            person_topics.append({"topic": None, "score": 1.0, "words": "", "category": cat})

    # ── Successor name quality validation ─────────────────────────────────────
    def is_valid_successor(email: str, name: str) -> bool:
        """Return True only if this candidate is a real person with a clean name."""
        if not email or should_remove(email):
            return False
        if not name:
            return False
        words = name.split()
        if len(words) < 2:
            return False
        # Reject names containing digits or most punctuation
        if re.search(r'[0-9@#$%^&*_+=\[\]{}|<>]', name):
            return False
        return True

    # ── Build lookup: departed person's topic → its category ──────────────────
    # Use ALL of this person's expertise entries (not just top-10 profile) so
    # successor topics ranked 11+ are still categorised correctly.
    all_person_ep = ep[ep["from"] == person]
    departed_topic_cat = {}
    for _, ep_row in all_person_ep.iterrows():
        t_id = int(ep_row["topic"])
        departed_topic_cat[t_id] = category_for(t_id)
    # Overlay with the richer profile entries (which have hand-crafted categories)
    for t in person_topics:
        if t["topic"] is not None:
            departed_topic_cat[t["topic"]] = t["category"]

    # Total unique categories: union of ep data + fallback profile entries.
    # Must be >= 1; perm_loss_categories is capped against this value.
    ep_categories         = {category_for(int(r["topic"])) for _, r in all_person_ep.iterrows()}
    profile_categories    = {t["category"] for t in person_topics if t.get("category")}
    all_person_categories = ep_categories | profile_categories
    total_categories      = max(len(all_person_categories), 1)

    # ── Successor analysis with role-gating ────────────────────────────────────
    # Primary successors MUST share the departed person's role_category.
    # Cross-role candidates are capped at readiness = 0.15.
    # Removed accounts and bad-name candidates are excluded entirely.
    succ_raw           = sim.get("successor_analysis", {})
    successor_analysis = []
    gap_topics         = 0
    key_topic_items    = list(succ_raw.items())[:5] if isinstance(succ_raw, dict) else []

    if isinstance(succ_raw, dict):
        for tid, candidates in key_topic_items:
            # Use the departed person's category for this topic (Fix 1)
            topic_int = int(tid) if str(tid).lstrip("-").isdigit() else tid
            # Fallback: use the departed person's role-based category rather than
            # the global topic keyword category (which may be "Corporate Communications"
            # or "General Operations" for generic topic IDs not in the person's ep).
            role_based_fallback = _ROLE_TO_TOPIC_CAT.get(dep_category, "General Operations")
            dep_topic_cat = departed_topic_cat.get(topic_int, role_based_fallback)

            # Apply role-gating + quality filtering
            gated = []
            for cand in candidates:
                cand_email = cand.get("candidate")
                cand_name  = display_name(cand_email) if cand_email else ""
                # Skip removed accounts and bad names (Fix 4 & 5)
                if not is_valid_successor(cand_email, cand_name):
                    continue
                cand_cat = person_to_category.get(
                    cand_email, role_category(
                        person_to_title.get(cand_email, "Administration")
                    )
                )
                r = float(cand.get("readiness", 0.0))
                if cand_cat != dep_category:
                    r = min(r, 0.15)
                gated.append({"candidate": cand_email, "readiness": round(r, 4)})
            gated.sort(key=lambda x: x["readiness"], reverse=True)

            # Check external hire gap: no same-role candidate with readiness > 0.30
            same_role_qualified = [
                c for c in gated
                if person_to_category.get(
                    c["candidate"],
                    role_category(person_to_title.get(c["candidate"], ""))
                ) == dep_category
                and c["readiness"] > 0.30
            ]
            if not same_role_qualified:
                gap_topics += 1

            best       = gated[0] if gated else {}
            cand_email = best.get("candidate")
            successor_analysis.append({
                "topic":           topic_int,
                "topic_words":     words_for(tid),
                "topic_category":  dep_topic_cat,   # Fix 1: departed person's category
                "best_successor":  cand_email,
                "successor_name":  display_name(cand_email) if cand_email else "",
                "readiness":       round(float(best.get("readiness", 0.0)), 4),
            })

    external_hire_gap = round(gap_topics / len(key_topic_items), 4) if key_topic_items else 0.0

    # ── Permanent losses on a category basis ──────────────────────────────────
    # Intersect with all_person_categories so the count can never exceed
    # total_categories and only counts categories present in the person's profile.
    perm_loss_topics = {l["topic"] for l in sim.get("permanent_losses", [])}
    if perm_loss_topics:
        perm_loss_cat_set    = {category_for(t) for t in perm_loss_topics} & all_person_categories
        perm_loss_categories = min(len(perm_loss_cat_set), total_categories)
    else:
        perm_loss_categories = 0

    # ── Positional impact score ────────────────────────────────────────────────
    pos_impact = positional_impact(role)
    q_name, q_color = compute_quadrant(round(float(row["risk_score"]), 4), round(pos_impact, 4))

    people_data.append({
        "person":             person,
        "display_name":       display_name(person),
        "role":               role,
        "role_category":      dep_category,
        "is_duplicate":       person.lower() in DUPLICATE_MAP,
        "canonical":          DUPLICATE_MAP.get(person.lower()),
        "risk_score":         round(float(row["risk_score"]), 4),
        "positional_impact":  round(pos_impact, 4),
        "quadrant":           q_name,
        "quadrant_color":     q_color,
        "description":        _lookup_description(person, display_name(person)) or (
            f"{q_name} classification. "
            f"{round(float(row['risk_score']), 4)*100:.1f}% knowledge risk across "
            f"{total_categories} topic categories with "
            f"{round(pos_impact * 100):.0f}% positional impact."
        ),
        "external_hire_gap":  external_hire_gap,
        "topic_monopoly":     int(row["topic_monopoly"]),
        "betweenness":        round(float(row["betweenness"]), 6),
        "weighted_degree":    float(row["weighted_degree"]),
        "topics_top_expert":  int(row["topics_top_expert"]),
        "component_delta":    int(row["component_delta"]),
        "simulated":          bool(row["simulated"]),
        "recovery_rates":     [round(r, 4) for r in recovery_rates],
        "permanent_losses":        sim.get("permanent_losses", []),
        "n_permanently_lost":      sim.get("n_permanently_lost", 0),
        "n_perm_loss_categories":  perm_loss_categories,
        "total_categories":        total_categories,
        "plateau_month":      sim.get("plateau_month"),
        "successor_analysis": successor_analysis,
        "topic_profile":      person_topics,
        "routing_by_month":   routing_by_month,
        "monthly_timeline":   timeline,
    })

print(f"  Built {len(people_data)} person records")

# ── Quadrant distribution ──────────────────────────────────────────────────────
from collections import Counter as _Counter
_qdist = _Counter(p["quadrant"] for p in people_data)
print("\nQuadrant distribution:")
for _q in ["Organizational Emergency", "Silent Threat", "Replaceable Executive", "Low Priority"]:
    print(f"  {_q:<30} {_qdist.get(_q, 0):>3}")

# ── Post-processing: recompute X/Y categories from scratch ────────────────────
# Authoritative single-pass using topic_categories as the only source of truth.
# Normalises topic IDs (handles int / float / string from parquet/JSON),
# intersects perm-loss categories with the person's own profile categories so
# the count can NEVER exceed total_categories.
print("\nPost-processing X/Y categories (authoritative recompute)...")
_n_post_changed = 0
for _rec in people_data:
    _tp = _rec.get("topic_profile", [])

    # ── total_categories: from the already-built topic_profile ──
    _tp_cats = set()
    for _t in _tp:
        _tid = _t.get("topic")
        if _tid is not None:
            try:
                _key = str(int(float(_tid)))     # normalise 5.0 → "5"
                _tp_cats.add(topic_categories.get(_key, "General Operations"))
            except (ValueError, TypeError):
                _tp_cats.add(_t.get("category", "General Operations"))
        elif _t.get("category"):
            _tp_cats.add(_t["category"])          # fallback/override entries
    if not _tp_cats:
        _tp_cats = {"General Operations"}
    _new_total = max(len(_tp_cats), 1)

    # ── perm_loss_categories: normalise IDs, then intersect with _tp_cats ──
    _perm_cats = set()
    for _pl in _rec.get("permanent_losses", []):
        _ptid = _pl.get("topic")
        if _ptid is None:
            continue
        try:
            _pkey = str(int(float(_ptid)))
            _perm_cats.add(topic_categories.get(_pkey, "General Operations"))
        except (ValueError, TypeError):
            _perm_cats.add("General Operations")
    _perm_cats &= _tp_cats                        # can never exceed person's categories
    _new_perm   = min(len(_perm_cats), _new_total)

    _old_total = _rec["total_categories"]
    _old_perm  = _rec["n_perm_loss_categories"]
    if _old_total != _new_total or _old_perm != _new_perm:
        _n_post_changed += 1
        print(f"  FIXED  {_rec['display_name']:<30}  "
              f"perm {_old_perm}→{_new_perm}  total {_old_total}→{_new_total}  "
              f"cats: {sorted(_tp_cats)}")
    _rec["total_categories"]       = _new_total
    _rec["n_perm_loss_categories"] = _new_perm

print(f"  Post-processing: {_n_post_changed} records fixed, "
      f"{len(people_data) - _n_post_changed} unchanged")

# ── Final sanity check ─────────────────────────────────────────────────────────
_final_broken = [
    (_p["display_name"], _p["n_perm_loss_categories"], _p["total_categories"])
    for _p in people_data
    if _p["total_categories"] == 0
    or _p["n_perm_loss_categories"] > _p["total_categories"]
    or _p["n_perm_loss_categories"] < 0
]
if _final_broken:
    print(f"  WARNING: {len(_final_broken)} violations remain after post-processing:")
    for _vn, _vp, _vt in _final_broken:
        print(f"    BROKEN: {_vn} — {_vp} of {_vt}")
else:
    print("  Sanity check PASSED — zero violations, all X/Y values valid.")

# ── Top 50 topic vulnerability ─────────────────────────────────────────────────
print("Building topic vulnerability data (top 50)...")

top50_vuln = vuln.nlargest(50, "vulnerability").copy()
topics_data = []
for _, row in top50_vuln.iterrows():
    try:
        top3 = json.loads(row["top3_experts"]) if isinstance(row["top3_experts"], str) else []
    except Exception:
        top3 = []
    for expert in top3:
        if isinstance(expert, dict) and "person" in expert:
            expert["display_name"] = display_name(expert["person"])

    tid = int(row["topic"])
    topics_data.append({
        "topic":              tid,
        "words":              words_for(tid),
        "category":           category_for(tid),
        "n_experts":          int(row["n_experts"]),
        "hhi":                round(float(row["hhi"]), 4),
        "vulnerability":      round(float(row["vulnerability"]), 6),
        "vulnerability_norm": round(float(row["vulnerability_norm"]), 4),
        "top3_experts":       top3,
    })

print(f"  Built {len(topics_data)} topic records")

# ── Graph data: top 100 most-connected nodes ───────────────────────────────────
print("Building graph data for top 100 nodes...")

risk_lookup = dict(zip(risk["person"], risk["risk_score"]))
wd_lookup   = dict(zip(risk["person"], risk["weighted_degree"]))

# Top 100 by degree (filtered), then guaranteed top-10 by risk score to ensure
# high-risk people (e.g. Pete Davis) appear even with lower degree
_by_degree = [n for n in sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)
              if not should_remove(n)][:100]

# ── Pete Davis debug ──────────────────────────────────────────────────────────
_pete = "pete.davis@enron.com"
print(f"\n  [DEBUG] pete.davis in graph:        {_pete in G}")
print(f"  [DEBUG] pete.davis in risk_lookup:  {_pete in risk_lookup}")
print(f"  [DEBUG] pete.davis should_remove:   {should_remove(_pete)}")
if _pete in risk_lookup:
    print(f"  [DEBUG] pete.davis risk_score:      {risk_lookup[_pete]:.4f}")
if _pete in G:
    print(f"  [DEBUG] pete.davis degree:          {G.degree(_pete)}")
print(f"  [DEBUG] pete.davis in by_degree:    {_pete in set(_by_degree)}")

_by_risk10 = [n for n in sorted(risk_lookup, key=lambda n: risk_lookup[n], reverse=True)
              if not should_remove(n) and n in G][:10]
print(f"  [DEBUG] top-10 by risk: {_by_risk10}")

_seen = set(_by_degree)
top100_nodes = _by_degree + [n for n in _by_risk10 if n not in _seen]
# Force-include Pete Davis if he's in the graph and not removed
if _pete in G and not should_remove(_pete) and _pete not in set(top100_nodes):
    top100_nodes.append(_pete)
    print(f"  [DEBUG] Force-added pete.davis to graph nodes")
print(f"  [DEBUG] pete.davis in merged list: {_pete in set(top100_nodes)}")
top100_set   = set(top100_nodes)

nodes_data = []
for node in top100_nodes:
    nodes_data.append({
        "id":              node,
        "display_name":    display_name(node),
        "risk_score":      round(float(risk_lookup.get(node, 0.0)), 4),
        "weighted_degree": float(wd_lookup.get(node, 0.0)),
        "degree":          G.degree(node),
    })

# Sort by risk_score descending — the dashboard JS takes slice(0,50), so
# highest-risk people (including Pete Davis at #2) must be at the front.
nodes_data.sort(key=lambda n: n["risk_score"], reverse=True)

print(f"\n  [DEBUG] Full graph_nodes list ({len(nodes_data)} nodes, sorted by risk):")
for i, nd in enumerate(nodes_data):
    flag = " ← PETE DAVIS" if nd["id"] == _pete else ""
    print(f"    {i+1:3d}. {nd['id']:<45}  risk={nd['risk_score']:.4f}  deg={nd['degree']}{flag}")
print(f"  [DEBUG] pete.davis in final nodes_data: {any(n['id'] == _pete for n in nodes_data)}")
print(f"  [DEBUG] pete.davis position in nodes_data: "
      f"{next((i for i, n in enumerate(nodes_data) if n['id'] == _pete), 'NOT FOUND')}")

edges_data  = []
seen_edges  = set()
for u, v, d in G.edges(data=True):
    if u in top100_set and v in top100_set:
        key = (min(u, v), max(u, v))
        if key not in seen_edges:
            seen_edges.add(key)
            edges_data.append({
                "source": u,
                "target": v,
                "weight": float(d.get("weight", 1)),
            })

print(f"  Nodes: {len(nodes_data)}, Edges: {len(edges_data)}")

# ── Pipeline stats ─────────────────────────────────────────────────────────────
total_perm_losses  = sum(p.get("n_permanently_lost", 0) for p in people_data)
avg_final_recovery = (
    sum(p["recovery_rates"][-1] for p in people_data if p["recovery_rates"]) / len(people_data)
    if people_data else 0.0
)
pipeline_stats = {
    "n_people_simulated":  len(people_data),
    "n_topics":            len(topic_words) or len(topics_data),
    "n_nodes":             len(nodes_data),
    "n_edges":             len(edges_data),
    "n_removed":           n_removed,
    "total_perm_losses":   total_perm_losses,
    "avg_final_recovery":  round(avg_final_recovery, 4),
}

# ── Assemble and save ──────────────────────────────────────────────────────────
dashboard_data = {
    "people":           people_data,
    "topics":           topics_data,
    "topic_words":      topic_words,
    "topic_categories": topic_categories,
    "pipeline_stats":   pipeline_stats,
    "graph": {
        "nodes": nodes_data,
        "edges": edges_data,
    },
}

with open("dashboard_data.json", "w") as f:
    json.dump(dashboard_data, f, separators=(",", ":"))

size_mb = os.path.getsize("dashboard_data.json") / 1_048_576
print(f"\nSaved dashboard_data.json  ({size_mb:.1f} MB)")
print("  people:", len(people_data))
print("  topics:", len(topics_data))
print("  topic_words:", len(topic_words))
print("  topic_categories:", len(topic_categories))
print("  graph nodes:", len(nodes_data), " edges:", len(edges_data))
print("  removed:", n_removed, "accounts")
