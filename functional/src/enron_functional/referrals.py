"""Referrals: messages that point a recipient to a third person ("check with Sara", "Sara will know").

Built on the main pipeline's resolved mentions (`mentions.parquet`): a
mention of a person who is neither the sender nor a recipient of the message
is a referral when the authored text around it carries a referral cue:

- before the name, an advice or request to go to the person: "please
  contact", "you should talk to", "check with", "ask", "get with", "touch
  base with", "follow up with", "run it by", "direct questions to", "refer
  you to", "reach out to", "speak with", "send/forward/give it to" — when the verb starts its sentence or
  clause, or follows "please", "pls", "feel free to", "you can/could/should/
  may/might/will need to/need to/want to/may want to", "try", "suggest you",
  "recommend you", "I would", "I'd" or "best to";
- after the name, a statement that the person can supply it: "will know",
  "would know", "can help", "can answer", "can tell you", "can assist", "is
  the (best/right) person/one/contact", "is your contact", "has the
  details/information/answer".

A possessive mention ("Sara's memo") is not a referral, and neither is a
first name followed by a different surname than the resolved person's.

Absence notices (`absence_notices.parquet`) are left out: who covers during an
absence is a separate signal. Mentions the main pipeline excluded (the sender,
offices, companies, abbreviations) are left out too.

Writes data/referrals.parquet (path, date, sender, person pointed to, the
matched cue and the sentence; it keeps message text) and
results/referrals.json (counts).

The check (`draw`, `score`) follows the absence check: rules frozen, a seeded
blind sample of detected referrals, labelled against labels/referral_guidelines.md.

Usage:
  uv run python -m enron_functional.referrals
  uv run python -m enron_functional.referrals draw
  uv run python -m enron_functional.referrals score
"""

from __future__ import annotations

import json
import re
import sys

import pandas as pd

from .absence_check import wilson
from .absences import split_sentences
from .config import ROOT, load_config
from .corpus import LOCAL_TIME, certified_sources

SOURCES = ("processed/messages.parquet", "processed/sender_people.parquet", "processed/identities.parquet",
           "processed/mentions.parquet")

_LEAD = (r"(?:please|pls|plz|feel free to|you (?:can|could|should|may|might|will need to|need to|want to|may want to"
         r"|might want to|'ll need to|will want to)|try|suggest you|recommend you|i would|i'd|best to|just)\s+")
_VERB = (r"(?:contact|call|talk to|talk with|speak to|speak with|check with|ask|get with|touch base with|follow up with"
         r"|coordinate with|reach out to|run (?:it|this|that) by|direct (?:any |all |your )?(?:questions|inquiries"
         r"|requests|comments)? ?to|refer (?:you|them|him|her) to|e-?mail|send (?:it|this|that|them) to|forward (?:it|this"
         r"|that|them) to|give (?:it|this|that|them) to)\s+")
BEFORE = re.compile(rf"(?:(?:^|[.;:!?,(\-]\s*)(?:and\s+)?|{_LEAD})(?:also\s+|then\s+|first\s+)?{_VERB}$", re.IGNORECASE)
AFTER = re.compile(r"^\s*(?:,\s*)?(?:will know|would know|should know|will be able to (?:help|answer|tell)"
                   r"|can help|could help|can answer|could answer|can tell you|could tell you|can assist|could assist"
                   r"|is (?:the |our |your )(?:best |right |main |key )?(?:person|one|contact|point person|expert)"
                   r"|is your contact|has the (?:details|info|information|answer|numbers|data))\b", re.IGNORECASE)


def find_referral(text: str, mention: str, person: str | None = None) -> tuple[str, str] | None:
    """(cue, sentence) when `mention` appears in `text` as a referral, else None.

    A possessive mention ("Sara's memo") is not a referral, and neither is a
    first name followed by a surname other than the resolved person's ("Tracy
    Warner" resolved to another Tracy).
    """
    if re.search(r"['’]s$", mention):
        return None
    surname = person.split()[-1].lower() if person and " " in person else None
    for sentence in split_sentences(text):
        for match in re.finditer(r"(?<![A-Za-z])" + re.escape(mention) + r"(?![a-z])", sentence):
            before, after = sentence[:match.start()], sentence[match.end():match.end() + 60]
            following = re.match(r"\s+([A-Z][a-z'\-]+)", after)
            if surname and " " not in mention.strip() and following and following.group(1).lower() != surname \
                    and following.group(1).lower() not in {"at", "or", "and", "on", "in", "to", "for", "about"}:
                continue
            possessive = re.match(r"['’]s\b", after)          # "see Sara's memo" points to the memo
            if (not possessive and (m := BEFORE.search(before))) or (m := AFTER.search(after)):
                return m.group(0).strip(" ,.;:"), sentence
    return None


def detect(mentions: pd.DataFrame, mail: pd.DataFrame, skip: set[str]) -> pd.DataFrame:
    """One row per (message, person pointed to)."""
    parties = mail.set_index("path")
    candidates = mentions[mentions["excluded"].isna() & ~mentions["path"].isin(skip)]
    candidates = candidates.drop_duplicates(["path", "mention", "person"])
    rows = []
    for path, group in candidates.groupby("path", sort=True):
        if path not in parties.index:
            continue
        message = parties.loc[path]
        involved = {message["sender_person"], *message["to_people"], *message["cc_people"]}
        found = set()
        for mention, person in zip(group["mention"], group["person"]):
            if person in involved or person in found:
                continue
            hit = find_referral(message["authored"], mention, person)
            if hit:
                found.add(person)
                rows.append({"path": path, "date": message["date"], "sender": message["sender_person"],
                             "person": person, "mention": mention, "cue": hit[0], "sentence": hit[1]})
    return pd.DataFrame(rows, columns=["path", "date", "sender", "person", "mention", "cue", "sentence"])


def load_mail(source) -> pd.DataFrame:
    from .corpus import person_mail
    mail = person_mail(source)
    authored = pd.read_parquet(source / "messages.parquet", columns=["path", "authored"])
    return mail.merge(authored, on="path", how="left", validate="one_to_one")


def run(config: dict) -> None:
    source, data, results = (config["paths"][k] for k in ("source", "data", "results"))
    certified_sources(source, SOURCES)
    mentions = pd.read_parquet(source / "mentions.parquet")
    notices = set(pd.read_parquet(data / "absence_notices.parquet", columns=["path"])["path"])
    referrals = detect(mentions, load_mail(source), notices)
    referrals.to_parquet(data / "referrals.parquet", index=False)
    report = {"referrals": len(referrals), "messages": int(referrals["path"].nunique()),
              "people_pointed_to": int(referrals["person"].nunique()),
              "by_cue": referrals["cue"].str.lower().str.replace(r"\s+", " ", regex=True).value_counts().head(25).to_dict()}
    results.mkdir(parents=True, exist_ok=True)
    (results / "referrals.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


DEV_INSPECTED = ROOT / "labels" / "referral_dev_inspected_paths.txt"


def draw(config: dict) -> None:
    settings, data = config["referral_check"], config["paths"]["data"]
    referrals = pd.read_parquet(data / "referrals.parquet")
    messages = pd.read_parquet(config["paths"]["source"] / "messages.parquet", columns=["path", "subject", "authored"])
    seen = set(DEV_INSPECTED.read_text().split()) if DEV_INSPECTED.exists() else set()
    pool = referrals[~referrals["path"].isin(seen)]
    sample = pool.sample(settings["sample_size"], random_state=settings["seed"]).merge(messages, on="path")
    sample = sample.sample(frac=1, random_state=settings["seed"]).reset_index(drop=True)
    items, key = [], []
    for item_id, row in enumerate(sample.itertuples(index=False), start=1):
        sent = row.date.tz_convert(LOCAL_TIME)
        items.append({"id": item_id, "sent": f"{sent:%A, %B %-d, %Y}", "subject": row.subject,
                      "named_person": row.mention, "text": row.authored})
        key.append({"id": item_id, "path": row.path, "person": row.person, "cue": row.cue})
    out = data / "labels" / "referrals"
    out.mkdir(parents=True, exist_ok=True)
    (out / "items.json").write_text(json.dumps(items, indent=2) + "\n")
    (out / "key.json").write_text(json.dumps(key, indent=2) + "\n")
    (ROOT / "labels" / "referral_check_paths.txt").write_text("\n".join(sorted(k["path"] for k in key)) + "\n")
    print(f"drew {len(items)} of {len(pool):,} referrals (seed {settings['seed']}); {len(seen)} read before were left out")


def score(config: dict) -> None:
    folder, results = config["paths"]["data"] / "labels" / "referrals", config["paths"]["results"]
    key = {k["id"]: k for k in json.loads((folder / "key.json").read_text())}
    labels = {int(k): v for k, v in json.loads((folder / "labels.json").read_text()).items()}
    if set(labels) != set(key):
        raise SystemExit(f"labels cover {len(labels)} of {len(key)} items")
    answers = pd.Series([v["referral"] for v in labels.values()])
    decided = answers[answers != "unclear"]
    yes = int((decided == "yes").sum())
    report = {"items": len(labels), "answers": answers.value_counts().to_dict(), "of_decided": len(decided),
              "precision": round(yes / len(decided), 4) if len(decided) else None,
              "interval_95": wilson(yes, len(decided))}
    (results / "referral_check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main() -> None:
    config = load_config()
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    {"": run, "draw": draw, "score": score}.get(command, lambda c: sys.exit("usage: referrals [draw|score]"))(config)


if __name__ == "__main__":
    main()
