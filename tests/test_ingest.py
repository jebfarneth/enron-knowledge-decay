import io
import tarfile

import pyarrow.parquet as pq

from enron_importance.ingest import iter_archive, parse_message, write_messages

RAW = b"""Message-ID: <18782981.1075855378110.JavaMail.evans@thyme>
Date: Mon, 14 May 2001 16:39:00 -0700 (PDT)
From: phillip.allen@enron.com
To: tim.belden@enron.com, "John Doe" <John.Doe@Enron.com>,
\tTim.Belden@enron.com
Cc: jane.roe@enron.com
Subject: Re: West desk
 schedule
X-From: Phillip K Allen
X-To: Tim Belden <Tim Belden/Enron@EnronXGate>

Here is our forecast.
"""


def test_parse_message_fields():
    row = parse_message(RAW, "maildir/allen-p/_sent_mail/1.")
    assert row["custodian"] == "allen-p"
    assert row["folder"] == "_sent_mail"
    assert row["message_id"] == "<18782981.1075855378110.JavaMail.evans@thyme>"
    assert row["sender"] == "phillip.allen@enron.com"
    # Lower-cased, order kept, duplicates removed, folded header lines joined.
    assert row["to"] == ["tim.belden@enron.com", "john.doe@enron.com"]
    assert row["cc"] == ["jane.roe@enron.com"]
    assert row["subject"] == "Re: West desk schedule"
    assert row["x_from"] == "Phillip K Allen"
    assert row["body"].strip() == "Here is our forecast."
    assert str(row["date"]) == "2001-05-14 23:39:00+00:00"


def test_missing_and_malformed_headers_do_not_fail():
    row = parse_message(b"Subject: hello\n\nbody\n", "maildir/x/inbox/2.")
    assert row["message_id"] is None
    assert row["sender"] is None
    assert row["date"] is None
    assert row["to"] == []
    bad = parse_message(b"Date: not a date\nFrom: a@b.com\n\nx\n", "maildir/x/inbox/3.")
    assert bad["date"] is None and bad["sender"] == "a@b.com"


def test_archive_round_trip(tmp_path):
    archive = tmp_path / "corpus.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name, data in [("maildir/allen-p/_sent_mail/1.", RAW), ("maildir/allen-p/", None), ("README", b"x")]:
            info = tarfile.TarInfo(name)
            if data is None:
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    destination = tmp_path / "messages.parquet"
    assert write_messages(iter_archive(archive), destination, batch_size=1) == 1
    table = pq.read_table(destination).to_pylist()
    assert table[0]["sender"] == "phillip.allen@enron.com"
    assert table[0]["to"] == ["tim.belden@enron.com", "john.doe@enron.com"]
