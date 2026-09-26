"""Resolve senders and recipients to people.

Every message is attributed from its own evidence first: the X-From display
name of that message is normalized to a person key ("christopher calger").
Only a message with no usable display name falls back to the person its
address usually belongs to. Display names come in three shapes, all handled:

  "Christopher F Calger"
  "Calger, Christopher F. </O=ENRON/OU=NA/CN=RECIPIENTS/CN=CCALGER>"
  "Tim Belden <Tim Belden/HOU/ECT@ECT>"

Three rules refine the key, each backed by evidence in the headers:

* Aliases: two keys with the same last name that share an Exchange directory
  ID (CN=BMEYERS for "Albert Meyers" and "Bert Meyers") are one person.
  Shared announcement mailboxes (CN=MBX_...) never merge people.
* Homonyms: when one first/last key carries two different middle initials,
  each on at least `min_initial_support` messages ("Mark A Taylor" and
  "Mark E Taylor"), the key is split by initial. A message without an
  initial takes the initial its directory ID uses on at least
  `initial_share` of its initialled messages, or its address does when the
  address has at least `min_initialled` initialled messages; otherwise it
  stays on the ambiguous first/last key.
* Go-by names: a message signed with a middle name the address usually goes
  by ("Davis, Mark Dana" at the address of "Dana Davis") belongs to that
  person, and a key whose messages nearly all carry that middle name is an
  alias of it.
* Roles: names containing role words or numbers ("Legal Temp 3",
  "Office of the Chairman", "Conf. Room ECN2760"), and anything sent through
  a shared Exchange mailbox (CN=MBX_...), are typed `role` and never merged
  with each other or with a person. A comma followed by a job title
  ("George Wasaff, Global Strategic Sourcing") is read as name then title,
  not surname first.

Placeholder addresses (the CMU export's `no.address@enron.com`, the Notes
gateway's `40enron@enron.com`, and any address shared by several named
senders none of whom covers half its messages) are never resolved to a
person: their messages are attributed only by their own display name, and
mail sent to them is dropped.

Recipient-only addresses (people who never sent mail in the corpus) resolve
to a person only when the address is literally `first.last@` of a known
person; otherwise they stay unresolved address nodes, typed `list` when the
address looks like a distribution list.

Usage: uv run python -m enron_importance.identity
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

import pandas as pd

from .config import load_config

_BRACKETED = re.compile(r"<[^>]*>|\([^)]*\)")
_NON_NAME = re.compile(r"[^a-z0-9\s-]")
_SPACE = re.compile(r"\s+")
_CN = re.compile(r"CN=([A-Za-z0-9._-]+)>?\s*$")
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
ROLE_WORDS = {
    "office", "chairman", "temp", "team", "desk", "crawler", "notification", "notifications",
    "announcement", "announcements", "mailbox", "services", "department", "center", "committee",
    "communications", "resources", "administrator", "support", "group", "operations", "enron",
    "conf", "room", "hotline", "console", "parking", "transportation", "payroll", "registrar", "security",
    "helpdesk", "mailsweeper", "benefits",
}
# Words that mark the part after a comma as a job title, not a first name.
TITLE_WORDS = {
    "director", "manager", "president", "vp", "vice", "officer", "ceo", "coo", "cfo", "chairman",
    "counsel", "analyst", "specialist", "head", "lead", "senior", "sr", "associate", "executive",
}
_LIST_LOCAL = re.compile(r"(^|[._-])(dl|list|all|everyone|team|group)([._-]|$)")
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


def _words(display) -> list[str] | None:
    """Lower-cased name words in first-to-last order; None if not a personal name field."""
    if not isinstance(display, str):
        return None
    text = _BRACKETED.sub(" ", display).strip().strip('"').strip()
    if "@" in text or "/" in text:
        return None
    if "," in text:
        before, _, after = text.partition(",")
        if _is_name_then_title(before, after):
            text = before  # "George Wasaff, Global Strategic Sourcing"
        else:
            text = f"{after} {before}"  # "Calger, Christopher F."
    text = _NON_NAME.sub(" ", text.lower().replace("'", ""))
    return [w.strip("-") for w in _SPACE.split(text) if w.strip("-")]


def _is_name_then_title(before: str, after: str) -> bool:
    """True for "First Last, Title ..." rather than surname-first "Last, First M"."""
    name = [w for w in _NON_NAME.sub(" ", before.lower()).split() if w.strip("-") and w not in _SUFFIXES]
    rest = [w.strip(".").lower() for w in after.split()]
    return len(name) >= 2 and (len(rest) >= 3 or any(w in TITLE_WORDS for w in rest))


def _has_role_word(words) -> bool:
    return any(w in ROLE_WORDS or any(c.isdigit() for c in w) for w in words)


def is_role_key(key) -> bool:
    return isinstance(key, str) and "@" not in key and _has_role_word(key.split())


def normalize_name(display) -> str | None:
    """'Calger, Christopher F. </O=...>' -> 'christopher calger'; None if unusable.

    Role mailbox names keep every word, including numbers ('legal temp 3');
    names sent through a shared Exchange mailbox (CN=MBX_...) become
    'mailbox ...' role keys.
    """
    words = _words(display)
    if words is None:
        return None
    if (directory_id(display) or "").startswith("MBX_"):
        return "mailbox " + " ".join(words) if words else None  # shared mailbox, never a person
    if _has_role_word(words):
        return " ".join(words) if len(words) >= 2 else None
    words = [w for w in words if len(w) > 1 and w not in _SUFFIXES]  # drop initials and Jr./Sr./III
    if len(words) < 2:
        return None
    first = NICKNAMES.get(words[0], words[0])
    return f"{first} {words[-1]}"


def middle_initial(display) -> str | None:
    """'Mark E Taylor' or 'Taylor, Mark E.' -> 'e'; None when there is none."""
    words = _words(display)
    if not words or len(words) < 3:
        return None
    initials = [w for w in words[1:-1] if len(w) == 1 and w.isalpha()]
    return initials[0] if initials else None


def middle_names(display) -> list[str]:
    """Full middle names ('Davis, Mark Dana' -> ['dana']); initials are excluded."""
    words = _words(display)
    return [w for w in words[1:-1] if len(w) > 1 and w not in _SUFFIXES] if words and len(words) >= 3 else []


def directory_id(display) -> str | None:
    """Exchange directory ID at the end of an X-From ('.../CN=CCALGER>' -> 'CCALGER')."""
    if not isinstance(display, str):
        return None
    match = _CN.search(display)
    return match.group(1).upper() if match else None


def _dominant(values: pd.Series, share: float):
    """The most common value if it covers at least `share` of `values`, else None."""
    counts = values.value_counts()
    if counts.empty or counts.iloc[0] / counts.sum() < share:
        return None
    return counts.index[0]


def entity_type(key, ambiguous=frozenset()) -> str:
    if not isinstance(key, str):
        return "placeholder"
    if "@" in key:
        return "list" if _LIST_LOCAL.search(key.split("@")[0]) else "address"
    if is_role_key(key):
        return "role"
    return "ambiguous" if key in ambiguous else "person"


def resolve_people(messages: pd.DataFrame, internal_domain: str, placeholders=(),
                   min_initial_support: int = 5, initial_share: float = 2 / 3, min_initialled: int = 20,
                   go_by_share: float = 0.9) -> tuple[pd.Series, pd.DataFrame, dict[str, str], dict[str, str]]:
    """Attribute each message to a sender person and map addresses to people.

    `messages` needs `sender` and `x_from`. Returns `sender_person` (aligned to
    `messages`; None when unknown or external), one row per internal sender
    address with person_key, entity_type, n_messages and resolved_by, the
    aliases applied to name keys (name_key, person_key, evidence), and the
    entity type of every key used.
    """
    suffix = "@" + internal_domain
    frame = messages.loc[messages["sender"].fillna("").str.endswith(suffix), ["sender", "x_from"]].copy()
    frame["key"] = frame["x_from"].map(normalize_name)
    frame["initial"] = frame["x_from"].map(middle_initial)
    frame["cn"] = frame["x_from"].map(directory_id)
    # A name an address also sends through a shared Exchange mailbox is that mailbox,
    # whatever the header rendering ("Parking & Transportation" with or without CN=MBX_).
    mailbox_words = (frame.loc[frame["key"].fillna("").str.startswith("mailbox "), ["sender", "key"]]
                     .groupby("sender")["key"].agg(lambda keys: set(" ".join(keys).split())))
    shared = [isinstance(k, str) and not is_role_key(k) and s in mailbox_words.index and set(k.split()) <= mailbox_words[s]
              for s, k in zip(frame["sender"], frame["key"])]
    frame.loc[shared, "key"] = "mailbox " + frame.loc[shared, "key"]
    named = frame["key"].notna() & ~frame["key"].map(is_role_key)

    # Aliases: same last name under one (non-shared) directory ID.
    evidence: dict[str, str] = {}
    size = frame.loc[named, "key"].value_counts()
    alias: dict[str, str] = {}
    with_cn = frame[named & frame["cn"].notna() & ~frame["cn"].fillna("").str.startswith("MBX_")]
    for _, keys in with_cn.groupby("cn")["key"]:
        by_last: dict[str, set] = defaultdict(set)
        for key in set(keys):
            by_last[key.split()[-1]].add(key)
        for group in by_last.values():
            # The fuller first name becomes the key ("albert meyers", not "bert meyers").
            target = max(group, key=lambda k: (len(k.split()[0]), size.get(k, 0), k))
            alias.update({k: target for k in group if k != target})
            evidence.update({k: "directory ID" for k in group if k != target})
    frame["key"] = frame["key"].map(lambda k: alias.get(k, k))

    # Go-by middle names: "Davis, Mark Dana" at the address Dana Davis uses is Dana Davis.
    frame["go_by"] = [
        f"{middles[0]} {key.split()[-1]}" if isinstance(key, str) and middles else None
        for key, middles in zip(frame["key"], frame["x_from"].map(middle_names))
    ]
    modal_key = frame[named].groupby("sender")["key"].agg(lambda k: k.value_counts().index[0])
    at_address = (frame["go_by"].notna() & (frame["go_by"] != frame["key"])
                  & (frame["go_by"] == frame["sender"].map(modal_key)))
    for key, group in frame[frame["key"].isin(set(frame.loc[at_address, "key"]))].groupby("key"):
        # The whole key is an alias when nearly all its messages carry that go-by name.
        target = frame.loc[at_address & (frame["key"] == key), "go_by"].iloc[0]
        if target != key and (group["go_by"] == target).mean() >= go_by_share:
            alias[key] = target
            evidence[key] = "go-by name"
    # Every message with the same full name ("Mark Dana Davis") follows, at any address.
    validated = set(zip(frame.loc[at_address, "key"], frame.loc[at_address, "go_by"]))
    follows = pd.Series([pair in validated for pair in zip(frame["key"], frame["go_by"])], index=frame.index)
    frame["key"] = frame["go_by"].where(follows, frame["key"].map(lambda k: alias.get(k, k)))

    # Homonyms: two well-supported middle initials under one key.
    counts = frame[named & frame["initial"].notna()].groupby(["key", "initial"]).size()
    counts = counts[counts >= min_initial_support]
    split = {key for key, n in counts.groupby(level="key").size().items() if n >= 2}
    supported = set(counts.index)
    initialled = frame[frame["key"].isin(split) & frame["initial"].notna()]
    by_cn = initialled.dropna(subset=["cn"]).groupby(["key", "cn"])["initial"].agg(lambda s: _dominant(s, initial_share))
    by_address = initialled.groupby(["key", "sender"])["initial"].agg(
        lambda s: _dominant(s, initial_share) if len(s) >= min_initialled else None)

    def person_of(sender, key, initial, cn):
        if not isinstance(key, str) or key not in split:
            return key if isinstance(key, str) else None
        if not isinstance(initial, str):
            initial = by_cn.get((key, cn)) or by_address.get((key, sender))
        if (key, initial) not in supported:
            return key  # ambiguous: stays on the shared first/last key
        first, last = key.split()[0], key.split()[-1]
        return f"{first} {initial} {last}"

    frame["person"] = [person_of(*row) for row in frame[["sender", "key", "initial", "cn"]].itertuples(index=False)]

    # Address -> person: the most common person among the address's named messages.
    totals = frame.groupby("sender").size()
    person_counts = frame.dropna(subset=["person"]).groupby(["sender", "person"]).size().rename("n").reset_index()
    person_counts = person_counts.sort_values(["sender", "n", "person"], ascending=[True, False, True])
    modal = person_counts.drop_duplicates("sender").set_index("sender")
    several = person_counts[person_counts["n"] >= 3].groupby("sender").size() >= 2
    shared = several[several].index[modal.loc[several[several].index, "n"] < totals[several[several].index] / 2]
    placeholder = set(placeholders) | set(shared)

    table = pd.DataFrame({"address": totals.index, "n_messages": totals.to_numpy()})
    table["person_key"] = table["address"].map(modal["person"])
    table["resolved_by"] = "display name"
    no_name = table["person_key"].isna()
    table.loc[no_name, "person_key"] = table.loc[no_name, "address"]
    table.loc[no_name, "resolved_by"] = "address only"
    is_placeholder = table["address"].isin(placeholder)
    table.loc[is_placeholder, "person_key"] = None
    table.loc[is_placeholder, "resolved_by"] = "placeholder"
    table["entity_type"] = table["person_key"].map(lambda k: entity_type(k, split))

    address_person = dict(zip(table["address"], table["person_key"]))
    sender_person = frame["person"].where(frame["person"].notna(), frame["sender"].map(address_person))
    keys = set(sender_person.dropna()) | set(table["person_key"].dropna())
    types = {key: entity_type(key, split) for key in sorted(keys)}
    aliases = pd.DataFrame([(k, v, evidence.get(k, "")) for k, v in sorted(alias.items())],
                           columns=["name_key", "person_key", "evidence"])
    return sender_person.reindex(messages.index), table.sort_values("address").reset_index(drop=True), aliases, types


def resolve_recipient(address: str, address_person: dict, people: set) -> str | None:
    """Person key for a recipient address: None for placeholders, the address itself when unresolved."""
    if address in address_person:
        person = address_person[address]
        return person if isinstance(person, str) else None
    parts = [p for p in address.split("@")[0].split(".") if p]
    if len(parts) == 2 and all(p.isalpha() and len(p) > 1 for p in parts):
        key = normalize_name(f"{parts[0]} {parts[1]}")
        if key in people:
            return key
    return address


def main(config: dict | None = None) -> None:
    config = config or load_config()
    spec = config["identity"]
    processed = config["paths"]["processed"]
    messages = pd.read_parquet(processed / "messages.parquet", columns=["path", "sender", "x_from", "analysis"])
    sender_person, table, aliases, types = resolve_people(
        messages, config["senders"]["internal_domain"], spec["placeholder_addresses"], spec["min_initial_support"],
        spec["initial_share"], spec["min_initialled"], spec["go_by_share"])
    table.to_parquet(processed / "identities.parquet", index=False)
    # Person text: analysis messages whose sender is attributed to a person
    # (not a role, list, bare address, ambiguous key or unknown author).
    person_text = messages["analysis"] & sender_person.map(types).eq("person")
    pd.DataFrame({"path": messages["path"], "sender_person": sender_person, "person_text": person_text}).to_parquet(
        processed / "sender_people.parquet", index=False)
    kinds = sender_person[messages["analysis"]].map(types).fillna("unknown").value_counts()
    funnel = {"analysis_messages": int(messages["analysis"].sum()),
              **{f"analysis_from_{kind}": int(n) for kind, n in kinds.items()},
              "person_text_messages": int(person_text.sum()),
              "person_text_people": int(sender_person[person_text].nunique())}
    (processed / "person_text.json").write_text(json.dumps(funnel, indent=2) + "\n")
    print(json.dumps(funnel, indent=2))
    aliases.to_parquet(processed / "name_aliases.parquet", index=False)
    pd.DataFrame(sorted(types.items()), columns=["person_key", "entity_type"]).to_parquet(
        processed / "person_types.parquet", index=False)
    keyed = table.dropna(subset=["person_key"]).drop_duplicates("person_key")
    print(f"{len(table):,} internal sender addresses -> {len(keyed):,} keys; {len(aliases)} name aliases")
    print(keyed["entity_type"].value_counts().to_string())
    print("placeholder addresses:", sorted(table.loc[table["resolved_by"] == "placeholder", "address"]))


if __name__ == "__main__":
    main()
