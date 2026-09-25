"""Resolve email addresses to people.

Enron staff often sent from several addresses: `christopher.calger@enron.com`
and the Exchange alias `f..calger@enron.com` are the same person. Each
address's most common X-From display name is normalized to a person key
("christopher calger"), and addresses sharing a key form one identity.
Display names come in three shapes, all handled:

  "Christopher F Calger"
  "Calger, Christopher F. </O=ENRON/OU=NA/CN=RECIPIENTS/CN=CCALGER>"
  "Tim Belden <Tim Belden/HOU/ECT@ECT>"

Addresses without a usable display name keep their own address as the key.
"""

from __future__ import annotations

import re

import pandas as pd

_BRACKETED = re.compile(r"<[^>]*>|\([^)]*\)")
_NON_LETTER = re.compile(r"[^a-z\s'-]")
_SPACE = re.compile(r"\s+")
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
# Common English nicknames mapped to one canonical first name, so "Tim Belden"
# and "Timothy Belden" resolve to the same person.
NICKNAMES = {
    "tim": "timothy", "mike": "michael", "chris": "christopher", "matt": "matthew",
    "jeff": "jeffrey", "jeffery": "jeffrey", "geoff": "geoffrey", "geoffery": "geoffrey",
    "larry": "lawrence", "doug": "douglas", "tom": "thomas", "brad": "bradley",
    "jim": "james", "jimmy": "james", "bill": "william", "bob": "robert", "rob": "robert",
    "dan": "daniel", "dave": "david", "steve": "steven", "stephen": "steven", "joe": "joseph",
    "ken": "kenneth", "rick": "richard", "rich": "richard", "dick": "richard",
    "andy": "andrew", "greg": "gregory", "ron": "ronald", "tony": "anthony",
    "sam": "samuel", "ben": "benjamin", "nick": "nicholas", "pete": "peter",
    "phil": "phillip", "philip": "phillip", "kate": "katherine", "kathy": "katherine",
    "liz": "elizabeth", "beth": "elizabeth", "sue": "susan", "jenny": "jennifer",
    "jen": "jennifer", "vince": "vincent", "ed": "edward", "ted": "edward",
    "stan": "stanley", "fred": "frederick",
}


def normalize_name(display: str | None) -> str | None:
    """'Calger, Christopher F. </O=...>' -> 'christopher calger'; None if unusable."""
    if not isinstance(display, str):
        return None
    text = _BRACKETED.sub(" ", display).strip().strip('"').strip()
    if "@" in text or "/" in text:
        return None
    if "," in text:
        last, _, first = text.partition(",")
        text = f"{first} {last}"
    words = [w.strip("'-") for w in _SPACE.split(_NON_LETTER.sub(" ", text.lower())) if w.strip("'-")]
    words = [w for w in words if len(w) > 1 and w not in _SUFFIXES]  # drop initials and Jr./Sr./III
    if len(words) < 2:
        return None
    first = NICKNAMES.get(words[0], words[0])
    return f"{first} {words[-1]}"


def build_identities(messages: pd.DataFrame, internal_domain: str) -> pd.DataFrame:
    """One row per internal sender address: address, person_key, display_name.

    `messages` needs `sender` and `x_from`.
    """
    internal = messages[messages["sender"].fillna("").str.endswith("@" + internal_domain)]
    names = (
        internal.assign(key=internal["x_from"].map(normalize_name))
        .dropna(subset=["key"])
        .groupby(["sender", "key"]).size().rename("n").reset_index()
        .sort_values(["sender", "n"], ascending=[True, False])
        .drop_duplicates("sender")
    )
    addresses = pd.DataFrame({"address": sorted(internal["sender"].dropna().unique())})
    table = addresses.merge(names.rename(columns={"sender": "address"}), on="address", how="left")
    table["person_key"] = table["key"].fillna(table["address"])
    table["display_name"] = table["key"].fillna(table["address"]).str.title()
    return table[["address", "person_key", "display_name"]]


def address_to_person(identities: pd.DataFrame) -> dict[str, str]:
    return dict(zip(identities["address"], identities["person_key"]))
