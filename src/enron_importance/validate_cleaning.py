"""Cross-check our quoted-text removal against an independent tool.

Compares `clean.authored_text` with `email_reply_parser` (Zapier's Python port
of GitHub's reply parser) on a fixed random sample of messages from the
deduplicated corpus. Reports how often the two agree and, where they differ,
which kinds of quoted material each leaves behind. Neither tool is ground
truth; disagreements are listed so they can be read.

Usage: uv run python -m enron_importance.validate_cleaning
"""

from __future__ import annotations

import json
import re

import pandas as pd
from email_reply_parser import EmailReplyParser

from .clean import authored_text
from .config import load_config

_SPACE = re.compile(r"\s+")
# Markers of quoted/forwarded material that should never remain in authored text.
RESIDUE = {
    "original_message": re.compile(r"-{2,}\s*Original Message", re.IGNORECASE),
    "forwarded_by": re.compile(r"Forwarded by", re.IGNORECASE),
    "quoted_header": re.compile(r"(?m)^\s*(From|To|Sent|cc|Subject):\s"),
    "angle_quote": re.compile(r"(?m)^\s*>"),
}


def normalized(text: str) -> str:
    return _SPACE.sub(" ", text or "").strip()


def token_jaccard(a: str, b: str) -> float:
    left, right = set(normalized(a).lower().split()), set(normalized(b).lower().split())
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def compare(bodies: pd.Series) -> pd.DataFrame:
    ours = bodies.map(authored_text)
    theirs = bodies.map(lambda b: EmailReplyParser.parse_reply(b if isinstance(b, str) else ""))
    frame = pd.DataFrame({"ours": ours, "theirs": theirs})
    frame["identical"] = frame["ours"].map(normalized) == frame["theirs"].map(normalized)
    frame["jaccard"] = [token_jaccard(a, b) for a, b in zip(frame["ours"], frame["theirs"])]
    for name, pattern in RESIDUE.items():
        frame[f"ours_{name}"] = frame["ours"].map(lambda t: bool(pattern.search(t)))
        frame[f"theirs_{name}"] = frame["theirs"].map(lambda t: bool(pattern.search(t)))
    return frame


def summary(frame: pd.DataFrame) -> dict:
    out = {
        "messages": len(frame),
        "identical": round(float(frame["identical"].mean()), 4),
        "token_jaccard_median": round(float(frame["jaccard"].median()), 4),
        "token_jaccard_ge_0_9": round(float((frame["jaccard"] >= 0.9).mean()), 4),
        "residue": {},
    }
    for name in RESIDUE:
        out["residue"][name] = {
            "ours": round(float(frame[f"ours_{name}"].mean()), 4),
            "email_reply_parser": round(float(frame[f"theirs_{name}"].mean()), 4),
        }
    return out


def main() -> None:
    config = load_config()
    spec = config["validation"]
    raw = pd.read_parquet(config["paths"]["interim"] / "messages_raw.parquet", columns=["path", "body"])
    kept = pd.read_parquet(config["paths"]["processed"] / "messages.parquet", columns=["path"])
    sample = raw[raw["path"].isin(set(kept["path"]))].sample(spec["sample_size"], random_state=config["random_seed"])
    frame = compare(sample["body"].reset_index(drop=True))
    result = summary(frame)
    results = config["paths"]["results"]
    results.mkdir(parents=True, exist_ok=True)
    (results / "cleaning_crosscheck.json").write_text(json.dumps(result, indent=2) + "\n")
    frame.assign(path=sample["path"].to_numpy())[~frame["identical"]].nsmallest(40, "jaccard")[
        ["path", "jaccard", "ours", "theirs"]
    ].to_csv(results / "cleaning_crosscheck_disagreements.csv", index=False)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
