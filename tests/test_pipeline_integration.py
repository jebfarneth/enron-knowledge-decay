"""Run the data stages end to end on a small generated corpus.

Each message reproduces a case from the 2026-09-25 audits, so these checks
exercise the current code on freshly generated data rather than reading
previously built outputs.
"""

import hashlib
import io
import tarfile

import pandas as pd

from enron_importance import identity, threads
from enron_importance.prepare import prepare
from enron_importance.provenance import stale_reasons


def email(message_id, sender, to, subject, body, date="Tue, 1 May 2001 09:00:00 -0500", x_from=""):
    return (f"Message-ID: <{message_id}>\nDate: {date}\nFrom: {sender}\nTo: {to}\nSubject: {subject}\n"
            f"X-From: {x_from}\n\n{body}\n").encode()


def corpus():
    files = {
        "maildir/x/inbox/1.": email(1, "no.address@enron.com", "a@enron.com", "News", "Company picnic moved.", x_from="Public Relations@ENRON"),
        "maildir/davis-d/sent/1.": email(2, "dana.davis@enron.com", "a@enron.com", "VAR", "Desk VAR is lowered.", x_from="Dana Davis"),
        "maildir/davis-d/sent/2.": email(3, "dana.davis@enron.com", "a@enron.com", "VAR 2", "New VAR limits attached.", x_from="Dana Davis"),
        "maildir/davis-d/sent/3.": email(4, "dana.davis@enron.com", "a@enron.com", "VAR 3", "Limits change again Monday.",
                                         x_from="Davis, Mark Dana </O=ENRON/OU=NA/CN=RECIPIENTS/CN=MDAVIS>"),
        "maildir/x/inbox/2.": email(5, "tonai.lehr@enron.com", "a@enron.com", "Crescendo", "Calendar Entry\n\nBrief description:\nDate:",
                                    x_from="Tonai Lehr"),
        "maildir/mann-k/sent/1.": email(6, "kay.mann@enron.com", "mark.taylor@enron.com", "Turbine",
                                        "Can you review section 4 of the turbine contract before Friday? " * 3,
                                        date="Tue, 1 May 2001 06:00:00 -0500", x_from="Kay Mann"),
        # The same message exported with a shifted clock: a probable copy, never a parent.
        "maildir/taylor-m/inbox/1.": email(66, "kay.mann@enron.com", "mark.taylor@enron.com", "Turbine",
                                           "Can you review section 4 of the turbine contract before Friday? " * 3,
                                           date="Tue, 1 May 2001 09:00:00 -0500", x_from="Kay Mann"),
        "maildir/taylor-m/sent/1.": email(
            7, "mark.taylor@enron.com", "kay.mann@enron.com", "RE: Turbine",
            "Section 4 is fine.\n\n\nKay Mann@ENRON\n05/01/2001 09:00 AM\nTo: Mark Taylor/HOU/ECT@ECT, Ann \nLee/HOU/ECT@ECT, Bo \n"
            "Chan/HOU/ECT@ECT\ncc:\nSubject: Turbine\n\n" + "Can you review section 4 of the turbine contract before Friday? " * 3,
            date="Tue, 1 May 2001 10:30:00 -0500", x_from="Mark E Taylor"),
    }
    # Sara answers Tana, quoting her under a bare Lotus header; Marie wrote later on the same subject.
    ask = "Please send me the executed Dynegy ISDA master agreement by noon tomorrow if you can."
    files["maildir/jones-t/sent/1."] = email(8, "tana.jones@enron.com", "sara.shackleton@enron.com", "ISDA", ask,
                                             date="Tue, 1 May 2001 06:00:00 -0500", x_from="Tana Jones")
    files["maildir/heard-m/sent/1."] = email(9, "marie.heard@enron.com", "sara.shackleton@enron.com", "ISDA",
                                             "The Dynegy master went to the legal files last week.",
                                             date="Tue, 1 May 2001 07:00:00 -0500", x_from="Marie Heard")
    files["maildir/shackleton-s/sent/1."] = email(
        10, "sara.shackleton@enron.com", "tana.jones@enron.com, marie.heard@enron.com", "Re: ISDA",
        "Attached.\n\n\n\tTana Jones\n\t05/01/2001 06:00 AM\n\t\t\n\t\t To: Sara Shackleton/HOU/ECT@ECT\n\t\t cc: \n"
        "\t\t Subject: ISDA\n\nPlease send me the executed",  # the quote is cut short: no text match
        date="Tue, 1 May 2001 08:00:00 -0500", x_from="Sara Shackleton")
    for i in range(60):  # a feed account's hourly alerts, plus one message its owner wrote
        files[f"maildir/davis-p/inbox/{i}."] = email(
            100 + i, "pete.davis@enron.com", "a@enron.com", "Schedule Crawler",
            f"Start Date: 4/{i % 28 + 1}/01; HourAhead hour: {i % 24}; No ancillary schedules awarded.", x_from="Schedule Crawler")
    files["maildir/davis-p/sent/1."] = email(200, "pete.davis@enron.com", "a@enron.com", "Bug",
                                             "I reproduced the bug: the crawler posted false finals. Please watch the next import.",
                                             x_from="Pete Davis")
    for i in range(10):  # repeated approvals are speech acts; a repeated long report is routine text
        files[f"maildir/white-a/sent/{i}."] = email(300 + i, "angela.white@enron.com", "a@enron.com", f"Credit {i}", "Approved",
                                                   x_from="Angela White")
        files[f"maildir/white-a/sent/r{i}."] = email(400 + i, "angela.white@enron.com", "a@enron.com", f"Watch {i}",
                                                    "Attached is the weekly credit watch listing for all counterparties.",
                                                    x_from="Angela White")
    return files


def build(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    archive = raw / "corpus.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name, data in corpus().items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return {
        "corpus": {"url": "unused", "filename": "corpus.tar.gz", "bytes": archive.stat().st_size,
                   "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()},
        "paths": {"raw": raw, "interim": tmp_path / "interim", "processed": tmp_path / "processed"},
        "ingest": {"start": "1998-01-01", "end": "2002-12-31"},
        "dedupe": {"max_shift_hours": 8, "min_body_chars": 100},
        "senders": {"internal_domain": "enron.com", "min_messages": 50, "feed_share": 0.9, "top_templates": 3,
                    "routine_repeats": 10, "speech_act_words": 4},
        "identity": {"placeholder_addresses": ["no.address@enron.com"], "min_initial_support": 5, "initial_share": 2 / 3,
                     "min_initialled": 20, "go_by_share": 0.9},
        "threads": {"max_reply_days": 14},
    }


def test_generated_corpus_reproduces_the_audited_cases(tmp_path):
    config = build(tmp_path)
    prepare(config)
    identity.main(config)
    threads.main(config)
    assert stale_reasons(config, ["prepare", "identity", "threads"]) == []
    processed = config["paths"]["processed"]
    messages = pd.read_parquet(processed / "messages.parquet").set_index("path")
    people = pd.read_parquet(processed / "sender_people.parquet").set_index("path")["sender_person"]
    links = pd.read_parquet(processed / "links.parquet").set_index("path")

    assert pd.isna(people["maildir/x/inbox/1."])                                   # placeholder, no author
    person_text = pd.read_parquet(processed / "sender_people.parquet").set_index("path")["person_text"]
    assert not person_text["maildir/x/inbox/1."] and person_text["maildir/davis-p/sent/1."]
    assert {people[f"maildir/davis-d/sent/{i}."] for i in (1, 2, 3)} == {"dana davis"}  # go-by middle name
    assert messages.loc["maildir/x/inbox/2.", "structured"]                        # calendar entry without colon
    assert messages.loc["maildir/davis-p/inbox/5.", "automated"]                   # repeated alert
    assert messages.loc["maildir/davis-p/sent/1.", "analysis"]                     # the owner's own message
    assert messages.loc["maildir/white-a/sent/3.", "routine"] and messages.loc["maildir/white-a/sent/3.", "analysis"]
    assert not messages.loc["maildir/white-a/sent/r3.", "analysis"]                # long routine report
    assert messages.loc["maildir/taylor-m/sent/1.", "authored"] == "Section 4 is fine."  # wrapped To list cut
    assert messages.loc["maildir/taylor-m/inbox/1.", "probable_copy"]
    assert links.loc["maildir/taylor-m/sent/1.", "parent_path"] == "maildir/mann-k/sent/1."
    assert links.loc["maildir/taylor-m/sent/1.", "link_kind"] == "reply"
    # The quoted author, read from the bare Lotus header, picks Tana's message over Marie's later one.
    assert links.loc["maildir/shackleton-s/sent/1.", "parent_path"] == "maildir/jones-t/sent/1."
    assert links.loc["maildir/shackleton-s/sent/1.", "link_confidence"] == "medium"
