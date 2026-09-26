"""Reconstruct candidate reply links and threads.

Enron headers carry no In-Reply-To or References fields, so links are
inferred. Senders and recipients are compared as people (the per-message
attribution and recipient resolution from `identity.py`), so a reply to an
alias address still matches. An earlier message p is a candidate parent of
message m when:

1. p and m have the same non-empty normalized subject (Re:/Fw: removed),
2. m's sender was a recipient (To/Cc) of p,
3. p was sent before m, within `max_reply_days`,
4. there is direct evidence: m is addressed back to p's sender, or m's
   quoted text contains the opening of p's authored text,
5. p's quoted text does not contain m's opening (that would make p the reply),
6. p was not sent by m's own sender, and, when m's quoted section names
   whom it quotes ("From: Susan Scott") but p's text is not found in it, p
   was sent by that person.

Among candidates, the one whose text is quoted nearest the top of m's quoted
section is the parent (the message m directly answers); without quotation,
the latest addressed candidate. Automated messages, structured records and
probable time-shifted copies are never linked.

`link_evidence` records which evidence held. `link_kind` is "reply" when m
is addressed back to p's sender and "forward" when m only relays p's text to
others, whatever its subject prefix; `response_seconds` is set for replies
only.

These are inferred candidate parents, not observed replies. Messages with
empty or changed subjects are not linked, and a parent whose subject differs
leaves m linked to an earlier message of the thread.

Usage: uv run python -m enron_importance.threads
"""

from __future__ import annotations

import json
import re

import pandas as pd
import pyarrow.parquet as pq

from .clean import reply_start
from .config import load_config
from .dedupe import normalize_subject
from .identity import extra_recipients, normalize_name, resolve_recipient

_SPACE = re.compile(r"\s+")
PREFIX_CHARS = 60   # opening of a message's authored text used to recognise it when quoted
MIN_PREFIX_CHARS = 20


def _flat(text) -> str:
    return _SPACE.sub(" ", text if isinstance(text, str) else "").strip().lower()


def _prefix(authored) -> str | None:
    text = _flat(authored)[:PREFIX_CHARS]
    return text if len(text) >= MIN_PREFIX_CHARS else None


def link_replies(messages: pd.DataFrame, max_reply_days: int, eligible: pd.Series | None = None) -> pd.DataFrame:
    """Add reply_to (index of the inferred parent), link_evidence, link_kind, response_seconds and thread_id.

    `messages` needs sender, to, cc, subject and date, and body and authored
    for quotation evidence (either may be absent); `quoted_from`, when
    present, is the person named in the first quoted header. `eligible` marks
    messages that may be linked at all. The index must be unique.
    """
    frame = messages.copy()
    frame["_subject"] = frame["subject"].map(normalize_subject)
    frame["reply_to"] = pd.array([pd.NA] * len(frame), dtype="Int64")
    frame["link_evidence"] = pd.Series([None] * len(frame), index=frame.index, dtype=object)
    frame["link_kind"] = pd.Series([None] * len(frame), index=frame.index, dtype=object)
    frame["response_seconds"] = pd.array([pd.NA] * len(frame), dtype="Float64")
    bodies = frame["body"] if "body" in frame else pd.Series("", index=frame.index)
    quoted_senders = frame["quoted_from"] if "quoted_from" in frame else pd.Series(None, index=frame.index, dtype=object)
    authored = frame["authored"] if "authored" in frame else bodies
    window = pd.Timedelta(days=max_reply_days)
    candidates = frame["_subject"] != ""
    if eligible is not None:
        candidates &= eligible.reindex(frame.index, fill_value=False)

    for _, group in frame[candidates].groupby("_subject", sort=False):
        if len(group) < 2:
            continue
        group = group.sort_values("date", kind="stable")
        earlier: list[tuple] = []  # (index, date, sender, recipients, prefix, flat quoted text)
        for index, row in group.iterrows():
            sender = row["sender"]
            addressed_to = set(row["to"]) | set(row["cc"])
            body = bodies[index] if isinstance(bodies[index], str) else ""
            quoted = _flat(body[reply_start(body):])
            own = _prefix(authored[index])
            quoted_from = quoted_senders[index]
            best = None  # (rank, index, date, evidence, addressed)
            for prior_index, prior_date, prior_sender, recipients, prior_prefix, prior_quoted in reversed(earlier):
                if row["date"] - prior_date > window:
                    break
                if not sender or sender not in recipients or prior_date >= row["date"] or prior_sender == sender:
                    continue
                if own and len(own) >= 2 * MIN_PREFIX_CHARS and own in prior_quoted:
                    continue  # the earlier message already quotes this one
                addressed = prior_sender in addressed_to
                position = quoted.find(prior_prefix) if prior_prefix else -1
                if not addressed and position < 0:
                    continue
                if position < 0 and isinstance(quoted_from, str) and prior_sender != quoted_from:
                    continue  # the reply quotes someone else's message, which is not this one
                evidence = "+".join(name for name, held in [("addressed", addressed), ("quoted", position >= 0)] if held)
                # Quoted parents rank by how near the top they are quoted; then the latest addressed one.
                rank = (0, position) if position >= 0 else (1, 0)
                if best is None or rank < best[0]:
                    best = (rank, prior_index, prior_date, evidence, addressed)
            if best is not None:
                _, prior_index, prior_date, evidence, addressed = best
                kind = "reply" if addressed else "forward"
                frame.at[index, "reply_to"] = prior_index
                frame.at[index, "link_evidence"] = evidence
                frame.at[index, "link_kind"] = kind
                if kind == "reply":
                    frame.at[index, "response_seconds"] = (row["date"] - prior_date).total_seconds()
            earlier.append((index, row["date"], sender, addressed_to, own, quoted))

    frame["thread_id"] = _thread_ids(frame)
    return frame.drop(columns="_subject")


_QUOTED_FROM = re.compile(r"^[ \t>]*From:[ \t]*(?P<value>[^\n]+)", re.IGNORECASE | re.MULTILINE)
_LOTUS_FROM = re.compile(r"^[ \t]*(?P<value>[A-Z][^\n/@]{2,60})(?:@|/)[^\n]*\n[ \t]*\d{1,2}/\d{1,2}/\d{2,4}", re.MULTILINE)
_ADDRESS = re.compile(r"[\w.'+-]+@[\w-]+(?:\.[\w-]+)+")


def quoted_author(body, person_of_address, person_of_name) -> str | None:
    """The person named in the first quoted header of `body` (From: line or Lotus name line), or None."""
    if not isinstance(body, str):
        return None
    quoted = body[reply_start(body):]
    found = [m for m in (_QUOTED_FROM.search(quoted), _LOTUS_FROM.search(quoted)) if m]
    if not found:
        return None
    value = min(found, key=lambda m: m.start()).group("value")
    address = _ADDRESS.search(value)
    if address:
        return person_of_address(address.group(0).lower())
    return person_of_name(value.split(" on ")[0].split(" <")[0].strip())


def _thread_ids(frame: pd.DataFrame) -> pd.Series:
    """Union-find over reply links; a message's thread is its root's index."""
    parent = {index: index for index in frame.index}

    def root(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for index, prior in frame["reply_to"].dropna().items():
        a, b = root(index), root(int(prior))
        if a != b:
            parent[max(a, b)] = min(a, b)
    return pd.Series({index: root(index) for index in frame.index}, dtype="int64")


def main(config: dict | None = None) -> None:
    """Link messages as people: attributed senders, resolved recipients, bodies from the parsed cache."""
    config = config or load_config()
    processed = config["paths"]["processed"]
    columns = ["path", "sender", "to", "cc", "to_extra", "cc_extra", "subject", "date", "authored", "automated",
               "structured", "probable_copy"]
    messages = pd.read_parquet(processed / "messages.parquet", columns=columns)
    messages = messages.merge(pd.read_parquet(processed / "sender_people.parquet")[["path", "sender_person"]], on="path")
    raw = pq.read_table(config["paths"]["interim"] / "messages_raw.parquet", columns=["path", "body"]).to_pandas()
    messages = messages.merge(raw, on="path", how="left")
    identities = pd.read_parquet(processed / "identities.parquet")
    address_person = dict(zip(identities["address"], identities["person_key"]))
    people = set(identities.loc[identities["entity_type"] == "person", "person_key"])
    cache: dict[str, str | None] = {}

    def people_of(addresses) -> list[str]:
        out = []
        for address in addresses:
            if address not in cache:
                cache[address] = resolve_recipient(address, address_person, people)
            if cache[address] is not None:
                out.append(cache[address])
        return out

    frame = pd.DataFrame({
        "sender": messages["sender_person"].where(messages["sender_person"].notna(), messages["sender"]),
        "to": messages["to"].map(people_of),
        "cc": [people_of(cc) + extra_recipients(people_of(list(to) + list(cc)), list(te) + list(ce),
                                                lambda a: people_of([a])[0] if people_of([a]) else None, people)
               for to, cc, te, ce in zip(messages["to"], messages["cc"], messages["to_extra"], messages["cc_extra"])],
        "subject": messages["subject"], "date": messages["date"],
        "authored": messages["authored"], "body": messages["body"],
    })
    aliases = pd.read_parquet(processed / "name_aliases.parquet")
    alias = dict(zip(aliases["name_key"], aliases["person_key"]))

    def person_of_name(name):
        key = normalize_name(name)
        return alias.get(key, key) if key else None

    frame["quoted_from"] = [quoted_author(b, lambda a: (people_of([a]) or [None])[0], person_of_name)
                            for b in messages["body"]]
    eligible = ~messages["automated"] & ~messages["structured"] & ~messages["probable_copy"]
    linked = link_replies(frame, config["threads"]["max_reply_days"], eligible)
    parent_path = linked["reply_to"].map(lambda i: messages.at[int(i), "path"] if pd.notna(i) else None)
    links = pd.DataFrame({"path": messages["path"], "parent_path": parent_path, "link_evidence": linked["link_evidence"],
                          "link_kind": linked["link_kind"], "response_seconds": linked["response_seconds"],
                          "thread": linked["thread_id"].map(messages["path"])})
    links.to_parquet(processed / "links.parquet", index=False)
    counts = {"links": int(links["parent_path"].notna().sum()), "reply_links": int((links["link_kind"] == "reply").sum()),
              "forward_links": int((links["link_kind"] == "forward").sum()), "threads": int(links["thread"].nunique())}
    (processed / "links.json").write_text(json.dumps(counts, indent=2) + "\n")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
