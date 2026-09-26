"""Cross-check our quoted-text removal against an independent tool.

Compares `clean.authored_text` with `email_reply_parser` (Zapier's Python port
of GitHub's reply parser) on a fixed random sample of messages from the
deduplicated corpus. Reports how often the two agree after whitespace
normalization, how much of each message each tool keeps, and which quotation
markers each leaves behind. Neither tool is ground truth, and marker counts
alone reward deleting text: an empty cleaner leaves no markers at all, so it
is reported as a control next to both tools, together with how often each
tool returns nothing.

The sample seed (`validation.seed`) differs from the seed of the sample used
while the cleaner's rules were written, but the rules were still developed on
this corpus, so this is a consistency check, not a held-out accuracy estimate.

Usage: uv run python -m enron_importance.validate_cleaning
"""

from __future__ import annotations

import json
import re

import pandas as pd
from email_reply_parser import EmailReplyParser

from .clean import authored_text
from .config import load_config
from .provenance import record_stage

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
    raw = bodies.map(lambda b: b if isinstance(b, str) else "")
    frame = pd.DataFrame({"raw": raw, "ours": raw.map(authored_text), "theirs": raw.map(EmailReplyParser.parse_reply)})
    frame["agree"] = frame["ours"].map(normalized) == frame["theirs"].map(normalized)
    frame["jaccard"] = [token_jaccard(a, b) for a, b in zip(frame["ours"], frame["theirs"])]
    raw_chars = frame["raw"].map(lambda t: len(normalized(t))).replace(0, 1)
    for tool in ["ours", "theirs"]:
        frame[f"{tool}_kept"] = frame[tool].map(lambda t: len(normalized(t))) / raw_chars
        frame[f"{tool}_empty"] = frame[tool].map(normalized) == ""
        for name, pattern in RESIDUE.items():
            frame[f"{tool}_{name}"] = frame[tool].map(lambda t: bool(pattern.search(t)))
    return frame


def summary(frame: pd.DataFrame) -> dict:
    share = lambda column: round(float(frame[column].mean()), 4)  # noqa: E731
    nonempty_raw = frame["raw"].map(normalized) != ""
    out = {
        "messages": len(frame),
        "whitespace_normalized_agreement": share("agree"),
        "token_set_jaccard_median": round(float(frame["jaccard"].median()), 4),
        "token_set_jaccard_ge_0_9": round(float((frame["jaccard"] >= 0.9).mean()), 4),
        "empty_output": {"ours": share("ours_empty"), "email_reply_parser": share("theirs_empty"), "empty_cleaner": 1.0},
        "median_share_of_text_kept": {"ours": round(float(frame.loc[nonempty_raw, "ours_kept"].median()), 4),
                                      "email_reply_parser": round(float(frame.loc[nonempty_raw, "theirs_kept"].median()), 4),
                                      "empty_cleaner": 0.0},
        "residue": {},
    }
    for name in RESIDUE:
        out["residue"][name] = {"ours": share(f"ours_{name}"), "email_reply_parser": share(f"theirs_{name}"),
                                "empty_cleaner": 0.0}
    return out


def main() -> None:
    config = load_config()
    spec = config["validation"]
    raw = pd.read_parquet(config["paths"]["interim"] / "messages_raw.parquet", columns=["path", "body"])
    kept = pd.read_parquet(config["paths"]["processed"] / "messages.parquet", columns=["path"])
    sample = raw[raw["path"].isin(set(kept["path"]))].sample(spec["sample_size"], random_state=spec["seed"])
    frame = compare(sample["body"].reset_index(drop=True))
    result = summary(frame)
    results = config["paths"]["results"]
    results.mkdir(parents=True, exist_ok=True)
    (results / "cleaning_crosscheck.json").write_text(json.dumps(result, indent=2) + "\n")
    frame.assign(path=sample["path"].to_numpy())[~frame["agree"]].nsmallest(40, "jaccard")[
        ["path", "jaccard", "ours", "theirs"]
    ].to_csv(results / "cleaning_crosscheck_disagreements.csv", index=False)
    print(json.dumps(result, indent=2))
    record_stage(config, "crosscheck")


if __name__ == "__main__":
    main()
