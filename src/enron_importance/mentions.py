"""The mention network of Agarwal, Omuya, Zhang & Rambow (2014).

"You're the boss if people get mentioned to you": a person's dominance is
predicted by how many different people are mentioned to them in email.

1. Mentions: spaCy's English named-entity recognizer (en_core_web_sm; the
   paper used NYU's AceJet) finds PERSON mentions in the sender's own text of
   every analysis message, so quoted earlier messages are not counted again.
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
   (Out-MRD). Links to the recipient themselves are dropped;
   `third_party_mentioned_to` also drops mentions of the sender or of any
   recipient of the message, leaving only people talked about.

Resolution is checked with the paper's heuristic: when exactly one person
compatible with a mention is Cc'd on the message, that person is taken as
correct, and the resolver (which does not see the Cc list) is scored on those
cases.

Outputs
  data/processed/mentions.parquet           one row per resolved (message, recipient, mention)
  data/processed/mention_centrality.parquet  per person: mention_degree, mentioned_to, third_party_mentioned_to
  results/mention_resolution.json            resolution counts and the Cc check

Usage: uv run python -m enron_importance.mentions
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

import igraph as ig
import numpy as np
import pandas as pd

from .config import load_config
from .identity import NICKNAMES, resolve_recipient

_TOKEN = re.compile(r"[a-z]+")
MAX_CHARS = 5000  # longer authored texts are cut before tagging
UNREACHABLE = 255


def name_index(people: set[str]) -> dict[str, set[str]]:
    """Name variant -> person keys: full name, first name and its nicknames, last name, initials."""
    nicknames_of: dict[str, set[str]] = defaultdict(set)
    for nickname, canonical in NICKNAMES.items():
        nicknames_of[canonical].add(nickname)
    index: dict[str, set[str]] = defaultdict(set)
    for key in people:
        words = key.split()
        if len(words) < 2 or not all(w.isalpha() for w in words):
            continue
        first, last = words[0], words[-1]
        for given in {first} | nicknames_of.get(first, set()):
            index[given].add(key)
            index[f"{given} {last}"].add(key)
        index[last].add(key)
        index[first[0] + last[0]].add(key)  # initials, "J.S." -> "js"
    return index


def compatible(mention: str, index: dict[str, set[str]]) -> set[str]:
    """People whose names are compatible with a mention ("Jeff", "Mark Taylor", "J.S.")."""
    text = mention.lower().replace("'s", "")
    if re.fullmatch(r"\s*([a-z])\.?\s*([a-z])\.?\s*", text):
        return set(index.get("".join(re.findall(r"[a-z]", text)), ()))
    words = [w for w in _TOKEN.findall(text) if len(w) > 1]
    if not words:
        return set()
    if len(words) == 1:
        word = words[0]
        return set(index.get(word, ())) | set(index.get(NICKNAMES.get(word, word), ()))
    first, last = NICKNAMES.get(words[0], words[0]), words[-1]
    return set(index.get(f"{first} {last}", ())) | set(index.get(f"{words[0]} {last}", ()))


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


def tag_mentions(texts: pd.Series, nlp, batch_size: int = 256) -> list[list[str]]:
    """PERSON entity strings for each text."""
    docs = nlp.pipe((t[:MAX_CHARS] if isinstance(t, str) else "" for t in texts), batch_size=batch_size)
    return [[ent.text for ent in doc.ents if ent.label_ == "PERSON"] for doc in docs]


def mention_links(messages: pd.DataFrame, index: dict[str, set[str]], distances: Distances) -> tuple[pd.DataFrame, dict]:
    """Resolve mentions per (message, recipient) and return resolved rows plus the Cc check.

    `messages` needs path, sender_person, to_people, cc_people and mentions.
    """
    rows, counts = [], defaultdict(int)
    for path, sender, to, cc, mentions in zip(messages["path"], messages["sender_person"], messages["to_people"],
                                               messages["cc_people"], messages["mentions"]):
        recipients = [r for r in dict.fromkeys(list(to) + list(cc)) if r != sender]
        for mention in mentions:
            candidates = compatible(mention, index)
            counts["mentions"] += 1
            if not candidates:
                counts["no_compatible_person"] += 1
                continue
            cc_matches = candidates & set(cc)
            if len(cc_matches) == 1 and to:
                counts["cc_checks"] += 1
                guess = distances.resolve(sender, to[0], candidates)
                counts["cc_checks_correct"] += guess == next(iter(cc_matches))
                counts["cc_checks_unresolved"] += guess is None
            for recipient in recipients:
                person = distances.resolve(sender, recipient, candidates)
                counts["resolutions"] += 1
                if person is None:
                    counts["unresolved"] += 1
                    continue
                rows.append((path, sender, recipient, mention, person))
    return pd.DataFrame(rows, columns=["path", "sender", "recipient", "mention", "person"]), dict(counts)


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


def main(config: dict | None = None) -> None:
    import spacy

    config = config or load_config()
    processed, results = config["paths"]["processed"], config["paths"]["results"]
    messages = pd.read_parquet(processed / "messages.parquet", columns=["path", "to", "cc", "authored", "analysis"])
    messages = messages[messages["analysis"]].merge(pd.read_parquet(processed / "sender_people.parquet"), on="path")
    messages = messages[messages["sender_person"].notna()].reset_index(drop=True)
    identities = pd.read_parquet(processed / "identities.parquet")
    address_person = dict(zip(identities["address"], identities["person_key"]))
    types = pd.read_parquet(processed / "person_types.parquet")
    people = set(types.loc[types["entity_type"] == "person", "person_key"])
    resolve = lambda a: resolve_recipient(a, address_person, people)  # noqa: E731
    messages["to_people"] = messages["to"].map(lambda xs: [p for p in map(resolve, xs) if p])
    messages["cc_people"] = messages["cc"].map(lambda xs: [p for p in map(resolve, xs) if p])

    nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer", "attribute_ruler", "tagger"])
    messages["mentions"] = tag_mentions(messages["authored"], nlp)
    edges = pd.read_parquet(processed / "edges.parquet")
    graph_people = people & (set(edges["source"]) | set(edges["target"]))
    links, counts = mention_links(messages, name_index(graph_people), Distances(edges))
    links.to_parquet(processed / "mentions.parquet", index=False)
    parties = pd.Series([{s, *t, *c} for s, t, c in zip(messages["sender_person"], messages["to_people"], messages["cc_people"])],
                        index=messages["path"])
    measures = mention_centrality(links, parties)
    measures.to_parquet(processed / "mention_centrality.parquet", index=False)
    counts["messages_tagged"] = len(messages)
    counts["messages_with_mentions"] = int(messages["mentions"].map(bool).sum())
    counts["resolved_links"] = len(links)
    counts["people_with_mention_links"] = len(measures)
    if counts.get("cc_checks"):
        counts["cc_check_accuracy"] = round(counts["cc_checks_correct"] / counts["cc_checks"], 4)
    results.mkdir(parents=True, exist_ok=True)
    (results / "mention_resolution.json").write_text(json.dumps(counts, indent=2) + "\n")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
