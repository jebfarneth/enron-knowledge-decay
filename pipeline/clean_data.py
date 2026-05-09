#!/usr/bin/env python3
"""
clean_data.py — Enron name resolution and system-account removal.

Phase 1: Build email → display-name lookup from emails.csv X-From headers.
Phase 2: Apply REMOVE list and NAME_FIXES overrides.
Phase 3: Print all discovered/fixed/unknown names for verification.
Phase 4: Write clean_names.json for use by export_dashboard_data.py.

Usage:
  python3 clean_data.py
"""

import csv
import json
import re
import os
import pandas as pd

csv.field_size_limit(10_000_000)

# ── REMOVE list ────────────────────────────────────────────────────────────────
# Match on local part (before @). Any email whose local part starts with or
# equals one of these strings is excluded from all outputs.
REMOVE_LOCALS = {
    "transportation.parking",
    "technology.enron",
    "bodyshop",
    "40enron",
    "exchange.administrator",
    "outlook.team",
    "no.address",
    "info",            # info@david.se — design/marketing system
    "sap_security",
    "confadmin",       # Conference Administrator @ziffenergy.com
    "conadmin",        # alternate spelling
    "announcements.ubsw",
    "admin.enron",
    "enron_update",
    "announcements.enron",
    "enron.announcements",
    "hdmd",            # Downtown District — not an Enron person
    "ggreen2",         # Gary Green @txu.com — TXU counterparty in REMOVE list
    "store-news",      # Amazon.com marketing
    "store.news",
    "dm-dmcn5-help",   # YourFreePresent.com spam
    "dm-dmen5-help",
    "acomnes",         # Alan Comnes — external consultant, per spec
    "alb",             # alb@cpuc.ca.gov — regulator, per spec
}

# Also remove any full-domain matches (amazon.com marketing, dmlogix spam)
REMOVE_DOMAINS = {
    "amazon.com",
    "dmlogix.com",
    "david.se",
}

# ── NAME_FIXES ──────────────────────────────────────────────────────────────────
# Maps email LOCAL PART → corrected display name.
# Sources: X-From / X-To header scan of emails.csv (documented below).
#
# Format: "local_part": ("Display Name", "source note")
# The source note is for documentation only; only the display name is used.
#
# For exact-email overrides (when the same local part appears at multiple
# domains with different identities), see FULL_EMAIL_FIXES below.

NAME_FIXES = {
    # ── Known aliases / alternate addresses ─────────────────────────────────
    "klay":              ("Kenneth Lay",     "CEO alt address; confirmed by context"),
    "vkamins":           ("Vince Kaminski",  "X-To: Vincent Kaminski <vkamins@ect.enron.com>"),
    "jdasovic":          ("Jeff Dasovich",   "DUPLICATE of jeff.dasovich@enron.com — flag for merging"),

    # ── Exchange 'middle-initial.lastname' aliases ───────────────────────────
    # Enron Exchange assigned addresses as 'MiddleInitial..Lastname@enron.com'.
    # The X-From header gives the full Exchange display name.
    ".nelson":           ("Kimberly Nelson", "X-From: Nelson, Kimberly (ETS)"),
    ".taylor":           ("Mark Taylor",     "X-From: Taylor, Mark E (Legal)"),
    ".schuler":          ("Lance Schuler",   "X-From: Schuler, Lance (Legal)"),
    ".ward":             ("Kim Ward",        "X-From: Ward, Kim S (Houston)"),
    ".williams":         ("Jason Williams",  "X-From: Williams, Jason R (Credit)"),
    ".hall":             ("Steve Hall",      "X-From: Hall, Steve C. (Legal)"),
    ".palmer":           ("Mark Palmer",     "X-From: Palmer, Mark S. (ENW)"),

    # ── Double-dot Exchange aliases (MiddleInitial..Lastname) ───────────────
    "a..price":          ("Brent Price",     "X-From: Price, Brent A."),
    "a..connor":         ("Richard Connor",  "X-From: Connor, Richard A."),
    "b..sanders":        ("Richard Sanders", "X-From: Sanders, Richard B."),
    "m..scott":          ("Susan Scott",     "X-From: Scott, Susan M. — DUPLICATE of susan.scott@enron.com"),
    "j..kean":           ("Steven Kean",     "X-From: Kean, Steven J. — DUPLICATE of steven.kean@enron.com"),
    "m..presto":         ("Kevin Presto",    "X-From: Presto, Kevin M."),
    "a..roberts":        ("Mike Roberts",    "X-From: Roberts, Mike A."),
    "a..gomez":          ("Julie Gomez",     "X-From: Gomez, Julie A."),
    "k..allen":          ("Phillip Allen",   "X-From: Allen, Phillip K. — DUPLICATE of phillip.allen@enron.com"),
    "m..tholt":          ("Jane Tholt",      "X-From: Tholt, Jane M."),
    "a..shankman":       ("Jeffrey Shankman","X-From: Shankman, Jeffrey A."),
    "a..robison":        ("Michael Robison", "X-From: Robison, Michael A."),
    "a..howard":         ("Kevin Howard",    "X-From: Howard, Kevin A."),
    "a..hughes":         ("James Hughes",    "X-From: Hughes, James A."),
    "a..davis":          ("Sarah Davis",     "X-From: Davis, Sarah A."),
    "a..smith":          ("Chris Smith",     "X-From: Smith, Chris A."),
    "a..garcia":         ("Julie Garcia",    "X-From: Garcia, Julie A."),
    "a..johnson":        ("Heather Johnson", "X-From: Johnson, Heather A."),
    "a..lindholm":       ("Tod Lindholm",    "X-From: Lindholm, Tod A."),
    "a..hueter":         ("Barbara Hueter",  "X-From: Hueter, Barbara A."),
    "a..campos":         ("Sylvia Campos",   "X-From: Campos, Sylvia A."),
    "d..steffes":        ("James Steffes",   "X-From: Steffes, James D. (user guessed 'Dave', actual first name James)"),
    "l..denton":         ("Rhonda Denton",   "X-From: Denton, Rhonda L."),
    "l..kelly":          ("Katherine Kelly", "X-From: Kelly, Katherine L."),
    "e..moscoso":        ("Michael Moscoso", "X-From: Moscoso, Michael E."),

    # ── Bare walton@enron.com ─────────────────────────────────────────────────
    "walton":            ("Leann Walton",    "X-From: Walton, Leann (confirmed as exact sender)"),

    # ── External real people ─────────────────────────────────────────────────
    "anncrawford":       ("Ann Crawford",    "X-From: Crawford, Ann <AnnCrawford@aec.ca>"),
    "pgarlinger":        ("Pam Garlinger",   "X-From: Pam Garlinger <PGarlinger@rcocpa.com>"),
    "bhanlon":           ("Barbara Hanlon",  "X-From: Barbara Hanlon <BHANLON@isda.org> (not 'Bill Hanlon')"),
    "ttong":             ("Dowson Tong",     "X-From: Dowson Tong <ttong@jiss.com>"),
    "jmrtexas":          ("Jack Rains",      "X-From: Jack Rains <jmrtexas@swbell.net>"),
    "jjohns":            ("Jane Johns",      "X-From: Jane Johns <jjohns@lemle.com>"),
    "ajones":            ("Annie Jones",     "X-From: Annie R. Jones <AJones@uwtgc.org>"),
    "lcampbel":          ("Larry Campbell",  "X-To: Larry Campbell <lcampbel@enron.com>"),
    "cstone1":           ("Charlie Stone",   "X-To: Charlie Stone <cstone1@txu.com>"),
    "alamonsoff":        ("Amy Lamonsoff",   "X-From: Amy Lamonsoff <alamonsoff@riskwaters.com>"),
    "agasca":            ("Amy Gasca",       "X-From: agasca@newenergy.com (Amy Gasca)"),
    "dperlin":           ("Debra Perlingiere","X-To: Perlingiere, Debra"),
    "scorman":           ("Shelley Corman",  "X-cc: Corman, Shelley"),
    "dpratt":            ("David Pratt",     "X-From: Pratt, David L. <DPratt@winstead.com>"),
    "gwadsworth":        ("George Wadsworth","X-From: Wadsworth, George <gwadsworth@midf.com>"),
    "alewis":            ("Andrew Lewis",    "X-To: Andrew Lewis <alewis@enron.com>"),
    "csilva":            ("Colleen Silva",   "X-From: Colleen Silva <Csilva@redsky.com>"),
    "abrock":            ("Alex Brock",      "X-From: Brock, Alex <abrock@PoloRalphLauren.com>"),
    "aweller":           ("Andrea Weller",   "X-From: Weller, Andrea <AWeller@sel.com>"),
    "ian":               ("Ian Anderson",    "X-From: Ian Anderson <ian@isanderson.com>"),
    "martha":            ("Martha Amram",    "X-From: martha Amram <martha@glazecreek.com>"),
    "cabbie":            ("Carol Anne Brannan","X-From: carol anne brannan <cabbie@unm.edu>"),
    "aahyman":           ("Aretha Hyman",    "X-From: Hyman, Aretha A - KC-7 <aahyman@bpa.gov>"),
    "aleonard":          ("Alice Leonard",   "X-From: Leonard, Alice <ALeonard@caiso.com>"),
    "aaron":             ("Aaron Breidenbaugh","X-From: Aaron Breidenbaugh <aaron@global2000.net>"),
    "brbarkovich":       ("B.R. Barkovich",  "X-From: BRBarkovich <brbarkovich@earthlink.net>"),
    "abhijeet.naik":     ("Abhijeet Naik",   "X-From: Naik, Abhijeet"),
    "robert.jones":      ("Robert Jones",    "X-From: Robert W Jones"),
    "sbuchanan":         ("S. Buchanan",     "No display name found in headers; sbuchanan@mwe.com"),
    "ahafner2":          ("A. Hafner",       "No display name in headers; CSC contractor"),

    # ── Quoted / malformed local parts ───────────────────────────────────────
    "'todd'.delahoussaye": ("Todd Delahoussaye", "Local part has stray quotes; per spec"),
}

# Full-email overrides for cases where the same local part maps to different
# people at different domains (e.g., csilva@redsky.com vs csilva@uamericas.edu.ec)
FULL_EMAIL_FIXES = {
    "csilva@redsky.com":         "Colleen Silva",
    "csilva@uamericas.edu.ec":   "Christian Silva",
    "vkamins@ect.enron.com":     "Vince Kaminski",
    "vkamins@enron.com":         "Vince Kaminski",
}

# ── Duplicate / alias flags ─────────────────────────────────────────────────────
# Addresses that are known duplicates of another canonical address.
DUPLICATES = {
    "klay@enron.com":        "kenneth.lay@enron.com",
    "vkamins@enron.com":     "vince.j.kaminski@enron.com",
    "vkamins@ect.enron.com": "vince.j.kaminski@enron.com",
    "jdasovic@enron.com":    "jeff.dasovich@enron.com",
    "j..kean@enron.com":     "steven.kean@enron.com",
    "k..allen@enron.com":    "phillip.allen@enron.com",
    "m..scott@enron.com":    "susan.scott@enron.com",
}

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def local_part(email: str) -> str:
    return email.split("@")[0].lower()


def should_remove(email: str) -> bool:
    lp = local_part(email)
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain in REMOVE_DOMAINS:
        return True
    # Exact local-part match only — no prefix matching
    if lp in REMOVE_LOCALS:
        return True
    return False


def clean_xfrom(raw: str) -> str:
    """Extract a clean 'First Last' display name from an X-From value."""
    raw = raw.strip()
    # Strip Exchange DN suffix: "Name </O=ENRON/..."
    raw = re.sub(r"\s*</O=ENRON.*", "", raw, flags=re.IGNORECASE)
    # Strip angle-bracket email: "Name <email@...>"
    raw = re.sub(r"\s*<[^>]+>", "", raw)
    # Strip @ENRON suffix
    raw = re.sub(r"@ENRON.*", "", raw, flags=re.IGNORECASE)
    # Strip IMCEANOTES garbage
    raw = re.sub(r"<IMCEA.*", "", raw, flags=re.IGNORECASE)
    # Strip trailing department tags like " (ETS)", " (Legal)", " (ENW)"
    # Keep the name, drop the tag
    raw = re.sub(r"\s*\([^)]+\)\s*$", "", raw)
    # Strip leading/trailing quotes
    raw = raw.strip().strip('"').strip("'")
    # If still looks like "Lastname, Firstname [Middle]", invert it
    m = re.match(r"^([A-Za-z'\-]+),\s+([A-Za-z][A-Za-z '\-]*)$", raw)
    if m:
        raw = f"{m.group(2).strip()} {m.group(1).strip()}"
    # Collapse whitespace
    raw = " ".join(raw.split())
    return raw


# ══════════════════════════════════════════════════════════════════════════════
# Phase 1 — Scan emails.csv for X-From display names
# ══════════════════════════════════════════════════════════════════════════════

def build_name_lookup(csv_path: str) -> dict:
    """Scan emails.csv and return {email_addr: raw_xfrom_value}."""
    print(f"Scanning {csv_path} for X-From headers ...")
    lookup = {}
    count = 0
    with open(csv_path, "r", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            msg = row.get("message", "")
            fm = re.search(r"^From:\s*(.+)$", msg, re.MULTILINE)
            xm = re.search(r"^X-From:\s*(.+)$", msg, re.MULTILINE)
            if fm and xm:
                addr = fm.group(1).strip().lower()
                # Normalise "dept <.name@enron.com>" → ".name@enron.com"
                addr = re.sub(r"^[^<]+<([^>]+)>$", r"\1", addr).strip()
                xfrom = xm.group(1).strip()
                if addr not in lookup:
                    lookup[addr] = xfrom
            count += 1
            if count % 200_000 == 0:
                print(f"  ... {count:,} rows scanned ({len(lookup):,} addresses found)")
    print(f"Done — {count:,} rows, {len(lookup):,} unique sender addresses.\n")
    return lookup


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2 — Resolve display name for each address in risk_scores.parquet
# ══════════════════════════════════════════════════════════════════════════════

def resolve_name(email: str, raw_lookup: dict):
    """
    Return a clean display name for `email`, or None if unknown.
    Priority:
      1. FULL_EMAIL_FIXES (exact email override)
      2. NAME_FIXES keyed on local part
      3. Automatic discovery from raw_lookup (X-From scan)
    """
    email_lc = email.lower()
    lp = local_part(email_lc)

    if email_lc in FULL_EMAIL_FIXES:
        return FULL_EMAIL_FIXES[email_lc]

    if lp in NAME_FIXES:
        return NAME_FIXES[lp][0]

    if email_lc in raw_lookup:
        return clean_xfrom(raw_lookup[email_lc])

    return None


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # ── Load addresses from risk_scores (top 200 for dashboard) ─────────────
    print("Loading risk_scores.parquet ...")
    risk = pd.read_parquet("risk_scores.parquet")
    all_people = risk.head(200)["person"].dropna().tolist()
    print(f"  {len(all_people)} addresses in top-200 risk_scores\n")

    # ── Scan emails.csv ───────────────────────────────────────────────────────
    raw_lookup = build_name_lookup("emails.csv")

    # ── Categorise and resolve ────────────────────────────────────────────────
    removed    = []
    fixed      = []   # from NAME_FIXES or FULL_EMAIL_FIXES
    discovered = []   # from X-From scan only
    unknown    = []   # no name found, not removed
    duplicate  = []   # known alias of another address

    final_names: dict[str, str] = {}   # email → clean display name

    for email in sorted(all_people):
        if should_remove(email):
            removed.append(email)
            continue

        email_lc = email.lower()
        lp = local_part(email_lc)

        if email_lc in DUPLICATES:
            canonical = DUPLICATES[email_lc]
            display = resolve_name(email, raw_lookup) or email
            duplicate.append((email, display, canonical))
            final_names[email_lc] = display
            continue

        name = resolve_name(email, raw_lookup)
        if name:
            # Determine source
            if email_lc in FULL_EMAIL_FIXES or lp in NAME_FIXES:
                fixed.append((email, name))
            else:
                discovered.append((email, name))
            final_names[email_lc] = name
        else:
            # Fall back to formatting the email address itself
            fallback = " ".join(p.capitalize() for p in lp.replace(".", " ").replace("_", " ").split() if p)
            unknown.append((email, fallback))
            final_names[email_lc] = fallback

    # ── Print report ──────────────────────────────────────────────────────────
    print("=" * 72)
    print(f"REMOVED  ({len(removed)}) — system/non-person accounts excluded:")
    for e in removed:
        print(f"  REMOVE  {e}")

    print()
    print(f"DUPLICATES  ({len(duplicate)}) — aliases of canonical addresses:")
    for email, display, canonical in duplicate:
        print(f"  ALIAS   {email:<50s} -> {display}  (dup of {canonical})")

    print()
    print(f"NAME FIXES  ({len(fixed)}) — manually specified overrides:")
    for email, name in fixed:
        note = ""
        lp = local_part(email)
        if email.lower() in FULL_EMAIL_FIXES:
            note = "(full-email fix)"
        elif lp in NAME_FIXES:
            note = f"({NAME_FIXES[lp][1]})"
        print(f"  FIX     {email:<50s} -> {name}  {note}")

    print()
    print(f"DISCOVERED  ({len(discovered)}) — from X-From header scan:")
    for email, name in discovered:
        raw = raw_lookup.get(email.lower(), "")
        print(f"  AUTO    {email:<50s} -> {name}  [raw: {raw[:60]}]")

    print()
    print(f"UNKNOWN  ({len(unknown)}) — no name found, using formatted email:")
    for email, fallback in unknown:
        print(f"  ???     {email:<50s} -> {fallback}")

    print()
    print(f"TOTAL: {len(removed)} removed | {len(duplicate)} duplicates | "
          f"{len(fixed)} fixed | {len(discovered)} auto | {len(unknown)} unknown")

    # ── Write clean_names.json for use by export_dashboard_data.py ────────────
    output = {
        "display_names": final_names,
        "removed":       removed,
        "duplicates":    {e: c for e, _, c in duplicate},
    }
    with open("clean_names.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved clean_names.json  ({len(final_names)} name entries)")


if __name__ == "__main__":
    main()
