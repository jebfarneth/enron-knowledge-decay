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
  initial takes the initial its directory ID or address uses on at least
  `initial_share` of its initialled messages; otherwise it stays on the
  ambiguous first/last key.
* Roles: names containing role words or numbers ("Legal Temp 3",
  "Office of the Chairman") are role mailboxes, typed `role` and never merged
  with each other or with a person.

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
        last, _, first = text.partition(",")
        text = f"{first} {last}"
    text = _NON_NAME.sub(" ", text.lower().replace("'", ""))
    return [w.strip("-") for w in _SPACE.split(text) if w.strip("-")]


def is_role_key(key) -> bool:
    return isinstance(key, str) and "@" not in key and any(w in ROLE_WORDS or w.isdigit() for w in key.split())


def normalize_name(display) -> str | None:
    """'Calger, Christopher F. </O=...>' -> 'christopher calger'; None if unusable.

    Role mailbox names keep every word, including numbers ('legal temp 3').
    """
    words = _words(display)
    if words is None:
        return None
    if any(w in ROLE_WORDS or any(c.isdigit() for c in w) for w in words):
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
                   min_initial_support: int = 5, initial_share: float = 2 / 3
                   ) -> tuple[pd.Series, pd.DataFrame, dict[str, str]]:
    """Attribute each message to a sender person and map addresses to people.

    `messages` needs `sender` and `x_from`. Returns `sender_person` (aligned to
    `messages`; None when unknown or external), one row per internal sender
    address with person_key, entity_type, n_messages and resolved_by, and the
    directory-ID aliases applied to name keys.
    """
    suffix = "@" + internal_domain
    frame = messages.loc[messages["sender"].fillna("").str.endswith(suffix), ["sender", "x_from"]].copy()
    frame["key"] = frame["x_from"].map(normalize_name)
    frame["initial"] = frame["x_from"].map(middle_initial)
    frame["cn"] = frame["x_from"].map(directory_id)
    named = frame["key"].notna() & ~frame["key"].map(is_role_key)

    # Aliases: same last name under one (non-shared) directory ID.
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
    frame["key"] = frame["key"].map(lambda k: alias.get(k, k))

    # Homonyms: two well-supported middle initials under one key.
    counts = frame[named & frame["initial"].notna()].groupby(["key", "initial"]).size()
    counts = counts[counts >= min_initial_support]
    split = {key for key, n in counts.groupby(level="key").size().items() if n >= 2}
    supported = set(counts.index)
    initialled = frame[frame["key"].isin(split) & frame["initial"].notna()]
    by_cn = initialled.dropna(subset=["cn"]).groupby(["key", "cn"])["initial"].agg(lambda s: _dominant(s, initial_share))
    by_address = initialled.groupby(["key", "sender"])["initial"].agg(lambda s: _dominant(s, initial_share))

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
    return sender_person.reindex(messages.index), table.sort_values("address").reset_index(drop=True), alias


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


def main() -> None:
    config = load_config()
    spec = config["identity"]
    processed = config["paths"]["processed"]
    messages = pd.read_parquet(processed / "messages.parquet", columns=["path", "sender", "x_from"])
    sender_person, table, aliases = resolve_people(messages, config["senders"]["internal_domain"], spec["placeholder_addresses"],
                                          spec["min_initial_support"], spec["initial_share"])
    table.to_parquet(processed / "identities.parquet", index=False)
    pd.DataFrame({"path": messages["path"], "sender_person": sender_person}).to_parquet(
        processed / "sender_people.parquet", index=False)
    pd.DataFrame(sorted(aliases.items()), columns=["name_key", "person_key"]).to_parquet(
        processed / "name_aliases.parquet", index=False)
    keyed = table.dropna(subset=["person_key"]).drop_duplicates("person_key")
    print(f"{len(table):,} internal sender addresses -> {len(keyed):,} keys; {len(aliases)} directory-ID aliases")
    print(keyed["entity_type"].value_counts().to_string())
    print("placeholder addresses:", sorted(table.loc[table["resolved_by"] == "placeholder", "address"]))


if __name__ == "__main__":
    main()
