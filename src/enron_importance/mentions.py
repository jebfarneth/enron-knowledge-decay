"""The mention network of Agarwal, Omuya, Zhang & Rambow (2014).

"You're the boss if people get mentioned to you": a person's dominance is
predicted by how many different people are mentioned to them in email.

1. Mentions: spaCy's English named-entity recognizer (en_core_web_sm; the
   paper used NYU's AceJet) finds PERSON mentions in the estimated authored
   text of every analysis message (quoted earlier messages are removed where
   the cleaner recognizes them; residual quotations remain).
2. Resolution, as in the paper: a mention is compatible with a person when it
   matches their full name, first name (nicknames included), last name or
   initials ("J.S."). For each recipient r of a message from sender s, the
   mention resolves to the compatible person p minimizing d(s, p) + d(r, p),
   the hop distances in the undirected, unweighted email network. The paper
   does not say how ties are broken; here a tie, or no reachable compatible
   person, leaves the mention unresolved.
3. Network: an unweighted link between each recipient and each person
   resolved as mentioned to them. `mention_degree` is degree in the
   undirected network (the paper's best system, Deg-MRU) and
   `mentioned_to` the number of different people mentioned to a person
   (Out-MRD; the measure declared primary before the audit-4 rerun). Links
   to the recipient themselves are dropped; `third_party_mentioned_to` also
   drops mentions of the sender or of any recipient of the message, leaving
   only people talked about.

The main measures count only person-text messages (the sender is attributed
to a person, not a role, list, bare address or ambiguous key) and leave out
mentions that resolve to the sender (signatures and contact lines), follow an
office title ("Governor Davis"), precede a company word ("Williams
pipeline", on the same line) or are an abbreviation ("Ste."). `mention_degree_unfiltered` and
`mentioned_to_unfiltered` keep every resolved mention from every analysis
message with a sender person, the definition before audit 4.

Resolution is checked with the paper's heuristic: when exactly one person
compatible with a mention is Cc'd on the message, that person is taken as
correct, and the resolver (which does not see the Cc list) is scored on those
cases, separately for mentions with one compatible person (resolved whenever
reachable) and with several. It checks the resolver against the same email
network it uses, so it is a consistency check, not an independent accuracy.

Only the first MAX_CHARS characters of a message's text are tagged. Tags are
cached in data/processed/mention_tags.parquet by message path and text hash,
under a tagger identity (model name, version and weight files, spaCy
version, active components, character cap and tagging code), so a rerun only
tags changed text and a change to any of these retags everything; a cached
entry whose names are not at their recorded positions is retagged too.

Outputs
  data/processed/mentions.parquet           one row per resolved (message, recipient, mention), with why
                                             it is left out of the main measures, if it is
  data/processed/mention_centrality.parquet  per person: mention_degree, mentioned_to, third_party_mentioned_to,
                                             mention_degree_unfiltered, mentioned_to_unfiltered
  results/mention_resolution.json            resolution counts and the Cc check

Usage: uv run python -m enron_importance.mentions
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path

import igraph as ig
import numpy as np
import pandas as pd

from .config import load_config
from .identity import NICKNAMES, extra_recipients, resolve_recipient
from .provenance import record_stage, tree_hash

_TOKEN = re.compile(r"[a-z]+(?:-[a-z]+)*")
MAX_CHARS = 5000  # longer authored texts are cut before tagging
UNREACHABLE = 255
# An office title just before a name on the same line ("Governor Davis", "Sen. Feinstein"): a public figure.
_OFFICE = re.compile(r"\b(?:governor|gov\.|senator|sen\.|representative|rep\.|congress(?:man|woman)|"
                     r"assembly(?:man|woman|member)|mayor|judge|justice|commissioner)[ \t]+$", re.IGNORECASE)
# A company word just after a name on the same line, or ending it ("Williams pipeline", "Duke Energy"),
# unless a department word follows ("Power Group", "Gas desk" name a colleague's group).
_COMPANY_WORDS = r"pipeline|pipe line|co|corp|corporation|inc|llc|lp|l\.p|ltd|energy|gas|power|company|companies|capital|holdings|securities|bank"
_DEPARTMENT = r"group|desk|team|trading|marketing|origination|department|dept"
_COMPANY_AFTER = re.compile(rf"^[ \t]*(?:{_COMPANY_WORDS})\b(?![ \t]+(?:{_DEPARTMENT})\b)", re.IGNORECASE)
_COMPANY_END = re.compile(rf"\b(?:{_COMPANY_WORDS})\.?\s*$", re.IGNORECASE)
_ABBREVIATION = re.compile(r"\s*[A-Z][a-z]{1,3}\.\s*")
# Place abbreviations whose period spaCy may leave outside the name ("Ste" in "Ste. Aurelie").
_PLACE_ABBREVIATIONS = {"st", "ste", "mt", "ft", "pt"}
_INITIALS = re.compile(r"\s*[A-Z]\.\s*[A-Z]\.?\s*|\s*[A-Z]{2}\s*")


def name_index(people: set[str]) -> dict[str, set[str]]:
    """Name variant -> person keys: full name, first name and its nicknames, last name, and initials
    under their own keys ("j.s."), so a two-letter first name ("Ed") never matches initials."""
    nicknames_of: dict[str, set[str]] = defaultdict(set)
    for nickname, canonical in NICKNAMES.items():
        nicknames_of[canonical].add(nickname)
    index: dict[str, set[str]] = defaultdict(set)
    for key in people:
        words = key.split()
        if len(words) < 2 or not all(_TOKEN.fullmatch(w) for w in words):
            continue
        first, last = words[0], words[-1]
        for given in {first} | nicknames_of.get(first, set()):
            index[given].add(key)
            index[f"{given} {last}"].add(key)
        index[last].add(key)
        index[f"{first[0]}.{last[0]}."].add(key)  # initials, "J.S."
    return index


def compatible(mention: str, index: dict[str, set[str]]) -> set[str]:
    """People whose names are compatible with a mention ("Jeff", "Mark Taylor", "J.S.").

    A middle initial in the mention ("Mark E. Taylor") rules out people split
    off under another initial ("mark d taylor").
    """
    if _INITIALS.fullmatch(mention.replace("'s", "")):  # "J.S." or "JS", but not "Ed"
        first, last = re.findall(r"[a-z]", mention.lower())
        return set(index.get(f"{first}.{last}.", ()))
    text = mention.lower().replace("'s", "")
    tokens = _TOKEN.findall(text)
    words = [w for w in tokens if len(w) > 1]
    if not words:
        return set()
    if len(words) == 1:
        word = words[0]
        return set(index.get(word, ())) | set(index.get(NICKNAMES.get(word, word), ()))
    first, last = NICKNAMES.get(words[0], words[0]), words[-1]
    found = set(index.get(f"{first} {last}", ())) | set(index.get(f"{words[0]} {last}", ()))
    initials = [w for w in tokens[1:-1] if len(w) == 1]
    if initials:
        found = {key for key in found if len(key.split()) < 3 or key.split()[1] == initials[0]}
    return found


def nil_reason(mention: str, text, start: int | None) -> str | None:
    """Why a PERSON mention is probably not a colleague ("office", "company", "abbreviation"), or None.

    `start` is where the mention begins in `text` (the tagged text); without it only the mention itself is read.
    """
    if _ABBREVIATION.fullmatch(mention):
        return "abbreviation"
    if _COMPANY_END.search(mention):
        return "company"
    if start is None or not isinstance(text, str):
        return None
    end = start + len(mention)
    if mention.strip().lower() in _PLACE_ABBREVIATIONS and text[end:end + 1] == ".":
        return "abbreviation"
    if _OFFICE.search(text[max(0, start - 40):start]):
        return "office"
    if _COMPANY_AFTER.match(text[end:end + 40]):
        return "company"
    return None


class Distances:
    """Hop distances in the undirected, unweighted email network, computed per source on demand."""

    def __init__(self, edges: pd.DataFrame):
        self.graph = ig.Graph.TupleList(edges[["source", "target"]].itertuples(index=False), directed=False)
        self.graph.simplify()
        self.id = {name: i for i, name in enumerate(self.graph.vs["name"])}
        self.cache: dict[int, np.ndarray] = {}

    def row(self, node: str) -> np.ndarray | None:
        i = self.id.get(node)
        if i is None:
            return None
        if i not in self.cache:
            hops = np.array(self.graph.distances(source=[i])[0], dtype=float)
            self.cache[i] = np.where(np.isinf(hops), UNREACHABLE, np.minimum(hops, UNREACHABLE - 1)).astype(np.uint8)
        return self.cache[i]

    def resolve(self, sender: str, recipient: str, candidates: set[str]) -> str | None:
        """The unique candidate closest to both sender and recipient, or None."""
        from_sender, from_recipient = self.row(sender), self.row(recipient)
        if from_sender is None or from_recipient is None:
            return None
        scored = [(int(from_sender[self.id[c]]) + int(from_recipient[self.id[c]]), c) for c in candidates
                  if c in self.id and from_sender[self.id[c]] != UNREACHABLE and from_recipient[self.id[c]] != UNREACHABLE]
        if not scored:
            return None
        best = min(d for d, _ in scored)
        winners = [c for d, c in scored if d == best]
        return winners[0] if len(winners) == 1 else None


def tag_mentions(texts: pd.Series, nlp, batch_size: int = 256) -> list[list[tuple[str, int]]]:
    """PERSON entities in each text (its first MAX_CHARS characters), as (text, start character)."""
    docs = nlp.pipe((t[:MAX_CHARS] if isinstance(t, str) else "" for t in texts), batch_size=batch_size)
    return [[(ent.text, ent.start_char) for ent in doc.ents if ent.label_ == "PERSON"] for doc in docs]


def tagger_id(nlp) -> str:
    """Model name and version, its weight files, spaCy version, active components, character cap and
    tagging code, as one digest."""
    path = getattr(nlp, "path", None)
    spec = {"model": f"{nlp.meta['name']}-{nlp.meta['version']}", "weights": tree_hash(Path(path)) if path else None,
            "spacy": version("spacy"), "pipes": list(getattr(nlp, "pipe_names", [])), "max_chars": MAX_CHARS,
            "code": inspect.getsource(tag_mentions)}
    return hashlib.sha1(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def text_hash(text) -> str:
    return hashlib.sha1((text if isinstance(text, str) else "")[:MAX_CHARS].encode("utf-8")).hexdigest()


def cached_mentions(messages: pd.DataFrame, cache_path, nlp, chunk: int = 5000) -> pd.Series:
    """Tag each message's authored text, reusing earlier tags for unchanged text from the same tagger.

    Returns (mention, start) pairs per message. A cached entry is reused only
    when every name it holds is found at its recorded position in the text;
    otherwise the message is tagged again. The cache is saved after every
    `chunk` newly tagged messages, so an interrupted run loses at most one
    chunk.
    """
    tagger = tagger_id(nlp)
    keys = messages["path"] + "\x1f" + messages["authored"].map(text_hash)
    cached = {}
    if cache_path.exists():
        old = pd.read_parquet(cache_path)
        if "tagger" in old:
            old = old[old["tagger"] == tagger]
            cached = {key: list(zip(names, starts)) for key, names, starts in zip(old["key"], old["mentions"], old["starts"])}
    texts = messages["authored"].map(lambda t: t[:MAX_CHARS] if isinstance(t, str) else "")
    intact = [key in cached and all(0 <= start and text[start:start + len(name)] == name for name, start in cached[key])
              for key, text in zip(keys, texts)]
    missing = keys[~pd.Series(intact, index=keys.index)]

    def save():
        saved = pd.DataFrame({"key": list(cached), "tagger": tagger,
                              "mentions": [[m for m, _ in found] for found in cached.values()],
                              "starts": [[int(s) for _, s in found] for found in cached.values()]})
        partial = cache_path.with_suffix(".part")
        saved.to_parquet(partial, index=False)
        partial.replace(cache_path)

    for start in range(0, len(missing), chunk):  # save after every chunk, so an interrupted run resumes
        batch = missing.index[start:start + chunk]
        cached.update(zip(keys[batch], tag_mentions(messages.loc[batch, "authored"], nlp)))
        save()
    return keys.map(cached)


def mention_links(messages: pd.DataFrame, index: dict[str, set[str]], distances: Distances) -> tuple[pd.DataFrame, dict]:
    """Resolve mentions per (message, recipient) and return resolved rows plus the Cc check.

    `messages` needs path, sender_person, to_people, cc_people and mentions
    (strings, or (string, start) pairs with the tagged text in `authored`);
    `person_text`, when present, marks messages whose sender is a person.
    Each row's `excluded` says why it is left out of the main measures:
    "not_person_text", a nil_reason, "self" (it resolves to the sender), or
    None.
    """
    rows, counts = [], defaultdict(int)
    person_text = messages["person_text"] if "person_text" in messages else pd.Series(True, index=messages.index)
    texts = messages["authored"] if "authored" in messages else pd.Series(None, index=messages.index, dtype=object)
    for path, sender, to, cc, mentions, own, text in zip(messages["path"], messages["sender_person"], messages["to_people"],
                                                         messages["cc_people"], messages["mentions"], person_text, texts):
        recipients = [r for r in dict.fromkeys(list(to) + list(cc)) if r != sender]
        for item in mentions:
            mention, start = item if isinstance(item, tuple) else (item, None)
            candidates = compatible(mention, index)
            counts["mentions"] += 1
            if not candidates:
                counts["no_compatible_person"] += 1
                continue
            cc_matches = candidates & set(cc)
            if len(cc_matches) == 1 and to:
                kind = "single" if len(candidates) == 1 else "ambiguous"
                guess = distances.resolve(sender, to[0], candidates)
                for name in ("cc_checks", f"cc_checks_{kind}"):
                    counts[name] += 1
                    counts[f"{name}_correct"] += guess == next(iter(cc_matches))
                    counts[f"{name}_unresolved"] += guess is None
            reason = None if own else "not_person_text"
            reason = reason or nil_reason(mention, text, start)
            for recipient in recipients:
                person = distances.resolve(sender, recipient, candidates)
                counts["resolutions"] += 1
                if person is None:
                    counts["unresolved"] += 1
                    continue
                excluded = reason or ("self" if person == sender else None)
                if excluded:
                    counts[f"excluded_{excluded}"] += 1
                rows.append((path, sender, recipient, mention, person, excluded))
    columns = ["path", "sender", "recipient", "mention", "person", "excluded"]
    return pd.DataFrame(rows, columns=columns), dict(counts)


def mention_centrality(links: pd.DataFrame, parties: pd.Series) -> pd.DataFrame:
    """Per person: undirected degree (Deg-MRU), people mentioned to them (Out-MRD), and third-party only.

    `parties` maps each path to the set of people on that message (sender and recipients).
    """
    links = links[links["recipient"] != links["person"]]
    undirected = defaultdict(set)
    mentioned_to = defaultdict(set)
    third_party = defaultdict(set)
    on_message = links["path"].map(parties)
    for recipient, person, present in zip(links["recipient"], links["person"], on_message):
        undirected[recipient].add(person)
        undirected[person].add(recipient)
        mentioned_to[recipient].add(person)
        if person not in present:
            third_party[recipient].add(person)
    people = sorted(undirected)
    return pd.DataFrame({
        "person_key": people,
        "mention_degree": [len(undirected[p]) for p in people],
        "mentioned_to": [len(mentioned_to.get(p, ())) for p in people],
        "third_party_mentioned_to": [len(third_party.get(p, ())) for p in people],
    })


def mention_measures(links: pd.DataFrame, parties: pd.Series) -> pd.DataFrame:
    """The main measures from rows with no exclusion, and the unfiltered pair from every row."""
    measures = mention_centrality(links[links["excluded"].isna()], parties)
    unfiltered = mention_centrality(links, parties)[["person_key", "mention_degree", "mentioned_to"]]
    unfiltered.columns = ["person_key", "mention_degree_unfiltered", "mentioned_to_unfiltered"]
    measures = measures.merge(unfiltered, on="person_key", how="outer").fillna(0)
    counted = [c for c in measures if c != "person_key"]
    measures[counted] = measures[counted].astype(int)
    return measures.sort_values("person_key", ignore_index=True)


def main(config: dict | None = None) -> None:
    import spacy

    config = config or load_config()
    processed, results = config["paths"]["processed"], config["paths"]["results"]
    # Every analysis message with a sender person is tagged (the unfiltered measures read them all);
    # person_text, carried from sender_people, limits the main measures.
    messages = pd.read_parquet(processed / "messages.parquet",
                               columns=["path", "to", "cc", "to_extra", "cc_extra", "authored", "analysis"])
    messages = messages[messages["analysis"]].merge(pd.read_parquet(processed / "sender_people.parquet"), on="path")
    messages = messages[messages["sender_person"].notna()].reset_index(drop=True)
    identities = pd.read_parquet(processed / "identities.parquet")
    address_person = dict(zip(identities["address"], identities["person_key"]))
    types = pd.read_parquet(processed / "person_types.parquet")
    people = set(types.loc[types["entity_type"] == "person", "person_key"])
    resolve = lambda a: resolve_recipient(a, address_person, people)  # noqa: E731
    messages["to_people"] = messages["to"].map(lambda xs: [p for p in map(resolve, xs) if p])
    messages["cc_people"] = [
        [p for p in map(resolve, cc) if p] + extra_recipients([p for p in map(resolve, list(to) + list(cc)) if p],
                                                              list(te) + list(ce), resolve, people)
        for to, cc, te, ce in zip(messages["to"], messages["cc"], messages["to_extra"], messages["cc_extra"])
    ]

    # Only the entity recognizer is needed; it has its own embedding layer, so the shared
    # tok2vec (used only by the tagger and parser) is disabled too, halving the time.
    nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer", "attribute_ruler", "tagger", "tok2vec"])
    messages["mentions"] = cached_mentions(messages, processed / "mention_tags.parquet", nlp)
    edges = pd.read_parquet(processed / "edges.parquet")
    graph_people = people & (set(edges["source"]) | set(edges["target"]))
    links, counts = mention_links(messages, name_index(graph_people), Distances(edges))
    links.to_parquet(processed / "mentions.parquet", index=False)
    parties = pd.Series([{s, *t, *c} for s, t, c in zip(messages["sender_person"], messages["to_people"], messages["cc_people"])],
                        index=messages["path"])
    measures = mention_measures(links, parties)
    measures.to_parquet(processed / "mention_centrality.parquet", index=False)
    counts["messages_tagged"] = len(messages)
    counts["messages_with_mentions"] = int(messages["mentions"].map(bool).sum())
    counts["messages_person_text"] = int(messages["person_text"].sum())
    counts["resolved_links"] = len(links)
    counts["resolved_links_main"] = int(links["excluded"].isna().sum())
    counts["people_with_mention_links"] = len(measures)
    for name in ("cc_checks", "cc_checks_single", "cc_checks_ambiguous"):
        if counts.get(name):
            counts[name.replace("checks", "check") + "_accuracy"] = round(counts[f"{name}_correct"] / counts[name], 4)
    results.mkdir(parents=True, exist_ok=True)
    (results / "mention_resolution.json").write_text(json.dumps(counts, indent=2) + "\n")
    print(json.dumps(counts, indent=2))
    record_stage(config, "mentions")


if __name__ == "__main__":
    main()
